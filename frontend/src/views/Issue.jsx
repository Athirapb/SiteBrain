import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Attachment, Empty, Icon, Modal, Spinner, URGENCY_BG, fmtTime, useAsync, usePoll } from "../components/ui";
import { Sparkline } from "../components/charts";
import { FILE_TYPES, FileChips, MAX_FILES, MediaButtons, filesForm, useFiles, useVoiceNote } from "../components/media";

// The journey in the user's words: expert help is one of the two routes to a resolution
const JOURNEY = [
  ["Issue Reporting", "clipboard-text-outline"],
  ["Quick Analysis", "magnify"],
  ["Detailed Analysis", "head-question-outline"],
  ["Resolution", "wrench-outline"],
];
// helper replies that steer the conversation rather than answer it
const SOFT_REPLIES = new Set(["How do I check this?", "I can't check this", "Not sure", "Skip to the fix",
                              "How do I do this?", "I can't do this step", "Show all steps", "No, still a problem"]);
// replies that move the job forward: shown as action buttons, not as observations
const ACTION_REPLIES = new Set(["Done", "Yes, it's working normally", "No issue found, close session"]);
// replies that end the chat: the field operator confirms them first
const CLOSING_REPLIES = new Set(["Yes, it's working normally", "No issue found, close session"]);
const TONE = { warn: ["#fff7e6", "#b36b00"], info: ["#e8f2fd", "#1c6fc1"], ok: ["#e3f2d4", "#006400"] };

export const issueTitle = (symptom) => symptom || "Reported issue";
const timeOf = (iso) => (iso ? new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : "");

export default function Issue({ user, params, nav, notify, refreshShared }) {
  const sid = params.sessionId;
  const [sv, setSv] = useState(null);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [dragging, setDragging] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [closing, setClosing] = useState(null); // null, or {reply}: the closing reply (or the menu item) to confirm
  const [menu, setMenu] = useState(false);
  const [similar, setSimilar] = useState(false);
  const [liveData, setLiveData] = useState(false);
  const [dismissed, setDismissed] = useState(() => new Set()); // expert recommendations the reporter declined
  const [reading, setReading] = useState(false); // SiteBrain is reading an attachment
  const scrollRef = useRef(null);
  const composer = useFiles(notify);
  const isExpert = user.role === "expert";
  const canReport = user.role === "field_operator";
  const back = params.from || (isExpert ? "queue" : "issues");

  const load = useCallback(async (fn) => {
    setBusy(true);
    try {
      const v = await fn();
      setSv(v);
      return v;
    } catch (e) {
      notify(e.message, true);
      return null;
    } finally {
      setBusy(false);
    }
  }, [notify]);

  useEffect(() => { load(() => api.get(`/api/sessions/${sid}`)); }, [sid, load]);

  const s = sv?.session;
  const resolved = s && ["resolved", "closed"].includes(s.status);
  const withExpert = s?.mode === "expert";
  // the expert replies when they can, so an escalated issue refreshes in the background
  usePoll(() => {
    if (s && !busy) api.get(`/api/sessions/${s.id}`).then((v) => (v.messages.length !== sv.messages.length || v.session.status !== s.status ? setSv(v) : null)).catch(() => {});
  }, withExpert && !resolved ? 8000 : 0, [s?.id, withExpert, resolved, busy, sv?.messages.length]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [sv?.messages.length, busy]);

  const act = async (path, body) => {
    const v = await load(() => api.post(`/api/sessions/${sid}${path}`, body));
    if (v) refreshShared();
    return v;
  };

  const send = async (text, choices = []) => {
    text = (text || "").trim();
    if (!text || busy || !s) return null;
    setInput("");
    if (isExpert) return act("/expert-message", { text });
    setSv((cur) => ({ ...cur, messages: [...cur.messages, { id: "tmp", type: "user", text, author: user.name, created_at: new Date().toISOString() }] }));
    return act("/messages", { text, choices });
  };

  const submit = async () => {
    if (busy || !s) return;
    if (!composer.files.length) return send(input);
    if (composer.tooBig.length) return notify(`${composer.tooBig.map((f) => f.name).join(", ")} is over 10 MB`, true);
    const text = input.trim();
    setInput("");
    setReading(!!sv.media);
    const v = await act("/files", filesForm(composer.files, { text }));
    setReading(false);
    if (v) composer.clear();
    else setInput(text);
  };

  // photos, videos and voice notes for one check: filed as evidence (no reply from SiteBrain). While SiteBrain
  // troubleshoots it reads them, and returns what it read so the check can take the answer a photo shows
  const evidence = async (files, caption, checkId) => {
    const fd = filesForm(files, { caption, ...(checkId ? { check_id: checkId } : {}) });
    setReading(true);
    try {
      const v = await api.post(`/api/sessions/${sid}/files`, fd);
      setSv(v);
      const ev = [...v.messages].reverse().find((x) => x.evidence);
      const readings = (ev?.attachments || []).map((f) => f.analysis).filter(Boolean);
      if (!readings.length) notify(`${files.length > 1 ? `${files.length} files` : files[0].name} added`);
      return readings;
    } catch (e) { notify(e.message, true); return []; } finally { setReading(false); }
  };

  const reply = (text, choices) => {
    if (!CLOSING_REPLIES.has(text)) return send(text, choices);
    if (!canReport) return notify("Only the person who reported the issue can close it", true);
    setClosing({ reply: text });
  };

  const confirmClose = async (note) => {
    const v = closing.reply ? await send(closing.reply) : await act("/resolve", { note });
    if (v) setClosing(null);
  };

  const escalate = async ({ description, summary, files }) => {
    const v = await act("/escalate", filesForm(files, { description, summary }));
    if (v) setEscalating(false);
  };

  const shareResolution = async (body) => {
    const v = await act("/expert-message", body);
    if (v) setSharing(false);
  };

  const sendVoice = async (f) => {
    if (busy || !s) return;
    setReading(!!sv?.media);
    await act("/files", filesForm([f], { text: "" }));
    setReading(false);
  };
  const voice = useVoiceNote(sendVoice, (m) => notify(m, true));

  if (!sv) {
    return (
      <div className="page">
        {busy ? <Spinner text="Opening the issue…" /> : (
          <Empty icon="message-alert-outline" title="This issue couldn't be opened">
            <button className="btn ghost sm" onClick={() => nav(back)}>Back</button>
          </Empty>
        )}
      </div>
    );
  }

  // quick replies belong to the latest prompt until the operator answers (events don't count)
  const replyIdx = (() => {
    for (let i = sv.messages.length - 1; i >= 0; i--) {
      const m = sv.messages[i];
      if (m.type === "user" && !m.evidence) return -1;
      if (m.type === "solution") return -1;
      if (m.replies?.length) return i;
    }
    return -1;
  })();
  const types = sv.messages.map((m) => m.type);
  const firstCauses = types.indexOf("fishbone");
  const lastCauses = types.lastIndexOf("fishbone");
  const stageIdx = resolved ? JOURNEY.length : sv.stage.index;
  const canType = !resolved && (isExpert ? withExpert : canReport);
  const canSend = !busy && canType && (input.trim() || composer.files.length) && !composer.tooBig.length;
  const reporter = s.report?.reported_by || "the reporter";
  const showConfirmFix = canReport && !resolved && !!s.identified && withExpert;

  const placeholder = !canType ? (resolved ? "Issue closed — report a new issue if it comes back"
      : isExpert ? "Replies open once the issue is escalated to the experts" : "Read only")
    : composer.files.length ? "Add a message about the files (optional)"
    : isExpert ? `Reply to ${reporter}`
    : withExpert ? "Message the experts — they'll see it when they reply"
    : sv.survey ? "Answer the check above, or ask me anything"
    : sv.phase === "fix" ? "Tap Done when finished, or ask me anything"
    : sv.localizing ? "Name the equipment, or say Not sure"
    : "Type a message";

  return (
    <div className={`issue ${isExpert ? "with-summary" : ""}`}>
      <section className={`chat ${dragging ? "dragging" : ""}`}
               onDragOver={(e) => { if (canType && e.dataTransfer.types.includes("Files")) { e.preventDefault(); setDragging(true); } }}
               onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false); }}
               onDrop={(e) => { if (!canType) return; e.preventDefault(); setDragging(false); composer.add(e.dataTransfer.files); }}>
        <header className="issue-head">
          <button className="btn ghost round" onClick={() => nav(back)} title="Back" aria-label="Back"><Icon name="arrow-left" /></button>
          <div className="grow" style={{ minWidth: 0 }}>
            <div className="issue-title-lg" title={issueTitle(s.symptom)}>{issueTitle(s.symptom)}</div>
            <div className="issue-where">
              {[sv.equipment ? sv.equipment.name : "Equipment not identified yet", sv.area.name, s.id, s.report?.project].filter(Boolean).join(" · ")}
            </div>
            <div className="row wrap" style={{ gap: 6 }}>
              <span className="caption">Severity</span>
              <span className="tag" style={{ background: URGENCY_BG[s.severity], color: "#fff" }}>{s.severity}</span>
              {isExpert && <span className="caption">· Reported by {reporter}</span>}
            </div>
          </div>
          {resolved && <span className="status-text" style={{ color: s.status === "resolved" ? "var(--gps-green-mid)" : "var(--t50)" }}>{s.status === "resolved" ? "Resolved" : "Closed"}</span>}
          {isExpert && (
            <button className="btn ghost sm" onClick={() => setLiveData(true)} disabled={!sv.telemetry}><Icon name="chart-line" />Plant Live Data</button>
          )}
          {isExpert && withExpert && !resolved && (
            <button className="btn sm" disabled={busy} onClick={() => setSharing(true)}><Icon name="check-decagram-outline" />Share Resolution</button>
          )}
          {canReport && !resolved && (
            <button className="btn sm" disabled={busy} onClick={() => setClosing({})}><Icon name="check-circle-outline" />Close Issue</button>
          )}
          {canReport && !resolved && !withExpert && (
            <div className="menu-wrap">
              <button className="btn ghost round" aria-label="More actions" onClick={() => setMenu((x) => !x)}><Icon name="dots-vertical" /></button>
              {menu && (
                <div className="menu" onMouseLeave={() => setMenu(false)}>
                  <button onClick={() => { setMenu(false); setEscalating(true); }}><Icon name="account-arrow-up-outline" />Get expert help</button>
                </div>
              )}
            </div>
          )}
        </header>

        <div className="journey">
          {JOURNEY.map(([label, icon], i) => {
            const done = i < stageIdx;
            const active = i === stageIdx;
            return (
              <div key={label} className={`stage ${done ? "done" : active ? "active" : ""}`}>
                <span className="stage-dot"><Icon name={done ? "check" : icon} /></span>
                <span className="stage-label">{label}</span>
                {i < JOURNEY.length - 1 && <span className="stage-line" />}
              </div>
            );
          })}
        </div>
        {sv.interlocks.length > 0 && (
          <div className="interlock-strip">
            {sv.interlocks.map((i) => (
              <div key={i.id} className={`safety ${i.category === "interlock" ? "critical" : ""}`}>
                <Icon name={i.category === "interlock" ? "shield-lock-outline" : "shield-alert-outline"} />
                <div><b>Safety · </b>{i.action}</div>
              </div>
            ))}
          </div>
        )}

        <div className="msgs wa" ref={scrollRef}>
          {sv.messages.map((m, i) => (
            <Message key={m.id + "-" + i} m={m} sid={sid} busy={busy} mode={s.mode} isExpert={isExpert}
              showReplies={i === replyIdx && !busy && !resolved && !withExpert && canReport}
              onReply={reply}
              causes={m.type === "fishbone" ? { first: i === firstCauses, bones: i === lastCauses && sv.fishbone?.length ? sv.fishbone : m.bones } : null}
              surveyOpen={m.type === "survey" && !!sv.survey && !resolved && !withExpert && canReport}
              onSurvey={(body) => act("/survey", body)} onEvidence={evidence} reads={!!sv.media}
              offerHidden={dismissed.has(m.id) || withExpert || resolved || !canReport}
              onEscalate={() => setEscalating(true)}
              onDismissOffer={() => setDismissed((d) => new Set(d).add(m.id))} notify={notify} />
          ))}
          {busy && (
            <div className="row typing"><span /><span /><span /><span className="caption">{withExpert ? "Sending…" : reading ? "SiteBrain is listening to and looking at your files…" : "SiteBrain is typing…"}</span></div>
          )}
        </div>

        {showConfirmFix && (
          <div className="confirm-fix">
            <Icon name="check-decagram-outline" size={20} color="var(--gps-primary)" />
            <span className="grow">Did the expert's fix work?</span>
            <button className="btn" onClick={() => setClosing({})}>Yes, Resolve & Close</button>
          </div>
        )}
        {composer.files.length > 0 && <div className="composer-files"><FileChips files={composer.files} onRemove={composer.remove} /></div>}
        {voice.recording ? (
          <div className="composer"><div className="recording grow"><span className="rec-dot" />Recording voice note · {Math.floor(voice.secs / 60)}:{String(voice.secs % 60).padStart(2, "0")}
            <span className="grow" /><button className="btn ghost sm" onClick={voice.cancel}>Cancel</button>
            <button className="btn sm" onClick={voice.stop}><Icon name="stop" />Stop & Attach</button></div></div>
        ) : (
          <div className="composer">
            <label className={`icon-btn ${!canType || composer.files.length >= MAX_FILES ? "disabled" : ""}`} title="Attach photos, videos or files">
              <Icon name="paperclip" size={22} />
              <input type="file" multiple hidden accept={FILE_TYPES} disabled={!canType || composer.files.length >= MAX_FILES}
                     aria-label="Attach files" onChange={(e) => { composer.add(e.target.files); e.target.value = ""; }} />
            </label>
            <label className={`icon-btn ${!canType ? "disabled" : ""}`} title="Take a photo">
              <Icon name="camera-outline" size={22} />
              <input type="file" hidden accept="image/*" capture="environment" disabled={!canType} aria-label="Take a photo"
                     onChange={(e) => { composer.add(e.target.files); e.target.value = ""; }} />
            </label>
            <textarea rows={1} value={input} disabled={!canType} placeholder={placeholder}
              onChange={(e) => setInput(e.target.value)}
              onPaste={(e) => { if (e.clipboardData.files.length) { e.preventDefault(); composer.add(e.clipboardData.files); } }}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canSend) submit(); } }} />
            {input.trim() || composer.files.length ? (
              <button className="send-btn" onClick={submit} disabled={!canSend} aria-label="Send"><Icon name="send" size={22} /></button>
            ) : (
              <button className="send-btn" onClick={voice.start} disabled={!canType} aria-label="Record a voice note" title="Record a voice note">
                <Icon name="microphone" size={22} />
              </button>
            )}
          </div>
        )}
        {dragging && <div className="drop-hint"><Icon name="tray-arrow-down" size={28} />Drop files to attach them</div>}

        {!isExpert && sv.cases.length > 0 && (
          similar ? (
            <div className="similar-panel" role="dialog" aria-label="Similar past cases">
              <div className="row"><div className="card-title grow">Similar Past Cases</div>
                <button className="btn ghost round sm" onClick={() => setSimilar(false)} aria-label="Close"><Icon name="close" /></button></div>
              <SimilarCases cases={sv.cases} />
            </div>
          ) : (
            <button className="similar-fab" onClick={() => setSimilar(true)}>
              <Icon name="book-search-outline" size={18} />Similar Past Cases<span className="fab-count">{sv.cases.length}</span>
            </button>
          )
        )}
      </section>

      {isExpert && <IssueSummary sv={sv} onLiveData={() => setLiveData(true)} />}

      {escalating && <EscalateModal sid={sid} busy={busy} notify={notify} onClose={() => setEscalating(false)} onSubmit={escalate} />}
      {sharing && <ResolutionModal busy={busy} reporter={reporter} onClose={() => setSharing(false)} onSubmit={shareResolution} />}
      {closing && <CloseModal busy={busy} identified={!!s.identified} withExpert={withExpert} reply={closing.reply}
                              onClose={() => setClosing(null)} onConfirm={confirmClose} />}
      {liveData && <LiveDataModal sv={sv} onClose={() => setLiveData(false)} />}
    </div>
  );
}

// Why a check is asked: folded away so the message itself stays short
function Why({ text }) {
  return (
    <details className="why">
      <summary className="link-summary"><Icon name="lightbulb-on-outline" size={13} /> Why?</summary>
      <div className="purpose" style={{ paddingTop: 4 }}><span>{text}</span></div>
    </details>
  );
}

function SimilarCases({ cases }) {
  return cases.map((k) => (
    <div key={k.id} className="case-card">
      <div className="row">
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--gps-primary)" }}>{k.id}</span>
        <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 600 }}>{k.sim}% match</span>
      </div>
      <div style={{ color: "var(--t80)", lineHeight: 1.4 }}>{k.title}</div>
      <div className="caption" style={{ color: "var(--t60)", lineHeight: 1.45 }}><b>What fixed it · </b>{k.fix}</div>
    </div>
  ));
}

function Files({ sid, files }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="row wrap" style={{ gap: 8 }}>
        {files.map((f) => <Attachment key={f.id} file={f} path={`/api/sessions/${sid}/files/${f.id}`} />)}
      </div>
      {files.filter((f) => f.analysis).map((f) => <Reading key={f.id} a={f.analysis} name={files.length > 1 ? f.filename : null} />)}
    </div>
  );
}

const READ_ICON = { audio: "microphone-outline", image: "image-search-outline", video: "video-outline" };

// What SiteBrain heard or saw in an attachment
export function Reading({ a, name }) {
  if (a.error) return <div className="reading muted"><Icon name="alert-circle-outline" size={15} />{a.error} Tell me in words what it shows.</div>;
  const said = a.english || a.transcript;
  const sees = a.kind === "audio" ? null : a.description;
  return (
    <div className="reading">
      <Icon name={READ_ICON[a.kind] || "file-search-outline"} size={15} />
      <div className="grow" style={{ minWidth: 0 }}>
        {name && <div className="caption ellipsis">{name}</div>}
        {said && <div><span className="reading-label">Heard</span> “{said}”</div>}
        {a.transcript && a.english && a.transcript !== a.english && (
          <div className="caption">{a.language ? `${a.language[0].toUpperCase()}${a.language.slice(1)}: ` : ""}{a.transcript}</div>
        )}
        {sees && <div><span className="reading-label">{a.kind === "image" || a.kind === "video" ? "Sees" : "Read"}</span> {sees}</div>}
        {a.answer && <div className="reading-answer"><Icon name="check-circle-outline" size={14} />Taken as: <b>{a.answer}</b></div>}
        {!a.answer && a.hint && <div className="caption">Might show: {a.hint}</div>}
        {a.concern && <div className="reading-warn"><Icon name="alert-outline" size={14} />{a.concern}</div>}
      </div>
    </div>
  );
}

// Possible causes as one list, most likely first (the 6M structure stays in the engine)
function CausesCard({ bones, first }) {
  const all = (bones || []).flatMap((b) => b.causes)
    .sort((a, b) => (a.ruled_out - b.ruled_out) || b.likelihood - a.likelihood).slice(0, 6);
  if (!all.length) return null;
  const top = all.find((c) => !c.ruled_out);
  return (
    <div className="panel causes">
      <div className="overline">{first ? "Possible causes (initial analysis)" : "Possible causes · updated"}</div>
      {all.map((c) => (
        <div key={c.label} className={`cause-row ${c.ruled_out ? "out" : c === top ? "top" : ""}`}>
          <span className="cause-label">{c.label}{c.ruled_out && <span className="caption"> · ruled out</span>}</span>
          {!c.ruled_out && <span className="cause-bar"><span style={{ width: `${Math.max(4, Math.round(c.likelihood * 100))}%` }} /></span>}
          <span className="cause-pct">{c.ruled_out ? "" : `${Math.round(c.likelihood * 100)}%`}</span>
        </div>
      ))}
    </div>
  );
}

function Message({ m, sid, showReplies, onReply, onEscalate, onDismissOffer, offerHidden, causes, surveyOpen, onSurvey,
                   onEvidence, busy, isExpert, notify, reads }) {
  const replies = m.replies || [];
  if (m.type === "report" || m.type === "signoff") return null; // the report is the frozen header
  if (m.type === "survey") return <ChecksWizard m={m} open={surveyOpen} busy={busy} onSubmit={onSurvey} onEvidence={onEvidence} notify={notify} reads={reads} />;
  if (m.type === "user") {
    const files = m.attachments || [];
    const mine = !isExpert;
    return (
      <div className={`msg ${mine ? "out" : "in"}`}>
        {m.survey ? (
          <div className="bubble-user">
            <div className="overline" style={{ marginBottom: 6 }}>My check results</div>
            {m.survey.map((x, j) => <div key={j} className="survey-answer"><span className="caption">{x.q}</span><b>{x.a}</b></div>)}
            <span className="bubble-time">{timeOf(m.created_at)} <Icon name="check-all" size={14} /></span>
          </div>
        ) : (
          <div className={`bubble-user ${m.evidence ? "evidence" : ""}`}>
            {m.evidence && <div className="caption" style={{ marginBottom: 4 }}><Icon name="paperclip" size={13} /> {m.text}</div>}
            {!m.evidence && m.text}
            {files.length > 0 && <div style={{ marginTop: m.text && !m.evidence ? 8 : 0 }}><Files sid={sid} files={files} /></div>}
            <span className="bubble-time">{isExpert ? `${m.author || "Reporter"} · ` : ""}{timeOf(m.created_at)} <Icon name="check-all" size={14} /></span>
          </div>
        )}
      </div>
    );
  }
  if (m.type === "escalation") {
    return (
      <div className={`msg ${isExpert ? "in" : "out"}`}>
        <div className="bubble-user">
          <div className="overline" style={{ marginBottom: 4 }}>Sent to the experts · {m.ticket}</div>
          {m.summary && (
            <details className="chat-summary" open={isExpert}>
              <summary className="link-summary">Summary of the chat</summary>
              <div style={{ whiteSpace: "pre-wrap", paddingTop: 4 }}>{m.summary}</div>
            </details>
          )}
          {m.text ? <div>{m.text}</div> : <div className="caption">No description given.</div>}
          {(m.attachments || []).length > 0 && <div style={{ marginTop: 8 }}><Files sid={sid} files={m.attachments} /></div>}
          <span className="bubble-time">{timeOf(m.created_at)} <Icon name="check-all" size={14} /></span>
        </div>
      </div>
    );
  }
  if (m.type === "event") {
    const [bg, fg] = TONE[m.tone] || ["#eef0ec", "#555"];
    return (
      <div className="msg"><div className="event"><div className="pillx" style={{ background: bg }}><Icon name={m.icon} size={16} color={fg} /><span>{m.text}</span></div></div></div>
    );
  }
  if (m.type === "offer") {
    return offerHidden ? null : (
      <div className="msg in"><div className="bubble-agent offer">
        <div style={{ lineHeight: 1.5 }}>{m.text}</div>
        <div className="row wrap" style={{ gap: 8 }}>
          <button className="btn danger" onClick={onEscalate}><Icon name="account-arrow-up-outline" />Escalate to Technical Expert</button>
          <button className="btn soft" onClick={onDismissOffer}>Will try to resolve myself</button>
        </div>
      </div></div>
    );
  }

  const expert = !!m.expert;
  const who = <div className={`who ${expert ? "expert" : ""}`}>{m.who || "SiteBrain"}</div>;
  return (
    <div className={`msg ${isExpert && expert ? "out" : "in"}`}>
      {m.type === "agent" && (m.text || m.items?.length > 0 || m.fix_step) && (
        <div className={`bubble-agent ${expert ? "expert" : ""}`}>
          {who}
          {!m.side && m.fix_step && <span className="tag step-tag">Step {m.fix_step} of {m.fix_total}</span>}
          <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
          {(m.items || []).length > 0 && (
            <ul style={{ margin: "6px 0 0", paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4 }}>
              {m.items.map((x, j) => <li key={j} style={{ lineHeight: 1.45 }}>{x}</li>)}
            </ul>
          )}
          {(m.attachments || []).length > 0 && <div style={{ marginTop: 8 }}><Files sid={sid} files={m.attachments} /></div>}
          {m.side && m.prompt && showReplies && (
            <div className="purpose"><Icon name="arrow-u-left-top" size={14} /><span>Back to: {m.prompt}</span></div>
          )}
          {!m.side && m.purpose && <Why text={m.purpose} />}
          {m.safety && <div className="safety"><Icon name="shield-alert-outline" /><div><b>Keep it safe · </b>{m.safety}</div></div>}
          <span className="bubble-time">{timeOf(m.created_at)}</span>
        </div>
      )}
      {m.type === "analysis" && (
        <div className="bubble-agent">
          {who}
          <div>{m.text}</div>
          {(m.safety_rules || []).map((r) => <div key={r} className="safety"><Icon name="shield-alert-outline" /><div><b>Safety · </b>{r}</div></div>)}
          <span className="bubble-time">{timeOf(m.created_at)}</span>
        </div>
      )}
      {m.type === "fishbone" && causes && <div className="bubble-agent wide"><CausesCard bones={causes.bones} first={causes.first} /></div>}
      {m.type === "finding" && (
        <div className="bubble-agent wide">
          {who}
          <div className="panel finding">
            <div className="overline"><Icon name="magnify-scan" size={14} /> Here's what we found</div>
            <div style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.4 }}>{m.direct_cause}</div>
          </div>
          <span className="bubble-time">{timeOf(m.created_at)}</span>
        </div>
      )}
      {m.type === "solution" && (
        <div className="bubble-agent wide">
          {who}
          <div className="panel solution">
            <div className="overline"><Icon name="check-decagram-outline" size={14} /> {m.expert ? "Resolution from the expert" : "Why it happened"}</div>
            <div style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.4 }}>{m.root_cause}</div>
            {m.direct_cause && m.direct_cause !== m.root_cause && <div className="caption" style={{ color: "var(--t70)" }}>What failed: {m.direct_cause}</div>}
            {m.expert && (m.steps || []).length > 0 && (
              <ol style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 4 }}>{m.steps.map((x, j) => <li key={j}>{x}</li>)}</ol>
            )}
            {(m.why_chain || []).length > 0 && (
              <details>
                <summary className="link-summary">How we got here</summary>
                <ol style={{ margin: "6px 0 0", paddingLeft: 20 }}>
                  {m.why_chain.map((w, j) => <li key={j} className="caption" style={{ color: "var(--t70)", lineHeight: 1.5 }}>{w.why} <b>{w.because}</b></li>)}
                </ol>
              </details>
            )}
            {(m.preventive || []).length > 0 && (
              <details>
                <summary className="link-summary">Stop it coming back · {m.preventive.length}</summary>
                <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>{m.preventive.map((x, j) => <li key={j} className="caption" style={{ color: "var(--t70)", lineHeight: 1.5 }}>{x}</li>)}</ul>
              </details>
            )}
            {m.basis && <div className="caption">Based on {m.basis}</div>}
          </div>
          <span className="bubble-time">{timeOf(m.created_at)}</span>
        </div>
      )}
      {showReplies && replies.length > 0 && <Replies replies={replies} multi={!!m.multi} onReply={onReply} />}
    </div>
  );
}

// The condition checks, one at a time (most likely cause first); all the answers go in together at the end
function ChecksWizard({ m, open, busy, onSubmit, onEvidence, notify, reads }) {
  const qs = m.questions;
  const [idx, setIdx] = useState(0);
  const [picked, setPicked] = useState({}); // check id → options seen
  const [cant, setCant] = useState({});
  const [read, setRead] = useState({}); // check id → what SiteBrain read from its photos and recordings
  if (!open) {
    return (
      <div className="msg in"><div className="bubble-agent">
        <div className="who">SiteBrain</div>
        <div>{m.text}</div>
        <div className="caption"><Icon name="check-all" size={14} /> {qs.length} checks done</div>
      </div></div>
    );
  }
  const q = qs[idx];
  const sel = picked[q.id] || [];
  const answered = sel.length > 0 || !!cant[q.id];
  const toggle = (o) => {
    setCant((c) => ({ ...c, [q.id]: false }));
    setPicked((p) => ({ ...p, [q.id]: sel.includes(o) ? sel.filter((x) => x !== o) : [...sel, o] }));
  };
  const skip = () => { setCant((c) => ({ ...c, [q.id]: true })); setPicked((p) => ({ ...p, [q.id]: [] })); if (idx < qs.length - 1) setIdx(idx + 1); };
  const last = idx === qs.length - 1;
  const addEvidence = async (files) => {
    const qid = q.id;
    const readings = await onEvidence(files, `Check ${idx + 1}: ${q.text}`, qid);
    if (!readings.length) return;
    setRead((r) => ({ ...r, [qid]: [...(r[qid] || []), ...readings] }));
    const answer = readings.map((x) => x.answer).find(Boolean);
    if (answer && q.options.includes(answer)) {
      setCant((c) => ({ ...c, [qid]: false }));
      setPicked((p) => ({ ...p, [qid]: (p[qid] || []).includes(answer) ? p[qid] : [...(p[qid] || []), answer] }));
      notify(`From your ${readings.find((x) => x.answer).kind === "audio" ? "voice note" : "photo"}: ${answer}. Change it if that's not right.`);
    }
  };
  const submit = () => onSubmit({
    answers: Object.fromEntries(qs.filter((x) => (picked[x.id] || []).length).map((x) => [x.id, picked[x.id]])),
    skipped: qs.filter((x) => cant[x.id] || !(picked[x.id] || []).length).map((x) => x.id),
  });
  return (
    <div className="msg in">
      <div className="bubble-agent wide">
        <div className="who">SiteBrain</div>
        <div style={{ fontWeight: 600 }}>{m.text}</div>
        <div className="check-card">
          <div className="row" style={{ gap: 10 }}>
            <span className="overline grow">Check {idx + 1} of {qs.length}</span>
            <span className="check-dots">{qs.map((x, j) => (
              <span key={x.id} className={`cdot ${j === idx ? "cur" : (picked[x.id] || []).length || cant[x.id] ? "done" : ""}`} />
            ))}</span>
          </div>
          <div className="check-q">{q.text}</div>
          {q.purpose && <Why text={q.purpose} />}
          <div className="answers">
            {q.options.map((o) => {
              const on = sel.includes(o);
              return (
                <button key={o} className={`answer ${on ? "on" : ""}`} aria-pressed={on} disabled={busy} onClick={() => toggle(o)}>
                  <Icon name={on ? "checkbox-marked-circle" : "checkbox-blank-circle-outline"} size={18} />{o}
                </button>
              );
            })}
          </div>
          {q.how && (
            <details className="how"><summary className="link-summary">How do I check this?</summary>
              <div className="caption" style={{ color: "var(--t70)", paddingTop: 4, lineHeight: 1.5 }}>{q.how}</div></details>
          )}
          <MediaButtons compact full={false} disabled={busy} onError={(x) => notify(x, true)} onFiles={addEvidence} />
          {reads && !(read[q.id] || []).length && <div className="caption">SiteBrain looks at your photo or video and listens to your voice note.</div>}
          {(read[q.id] || []).map((a, j) => <Reading key={j} a={a} />)}
          <div className="row wrap" style={{ gap: 8 }}>
            {idx > 0 && <button className="btn ghost" disabled={busy} onClick={() => setIdx(idx - 1)}><Icon name="arrow-left" />Back</button>}
            <button className="btn soft" disabled={busy} onClick={skip}>I can't check this</button>
            <span className="grow" />
            {last ? (
              <button className="btn" disabled={busy || !answered} onClick={submit}>
                <Icon name="send" size={16} />Send Answers
              </button>
            ) : (
              <button className="btn" disabled={busy || !answered} onClick={() => setIdx(idx + 1)}>Next Check<Icon name="arrow-right" /></button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Quick replies: observations are answer chips; moving the job on (Done, Send) are action buttons
function Replies({ replies, multi, onReply }) {
  const [picked, setPicked] = useState([]);
  const answers = replies.filter((r) => !SOFT_REPLIES.has(r) && !ACTION_REPLIES.has(r));
  const actions = replies.filter((r) => ACTION_REPLIES.has(r));
  const soft = replies.filter((r) => SOFT_REPLIES.has(r));
  if (!multi || answers.length < 2) {
    return (
      <div className="replies">
        {answers.length > 0 && <div className="answers">{answers.map((r) => <button key={r} className="answer" onClick={() => onReply(r)}>{r}</button>)}</div>}
        <div className="row wrap" style={{ gap: 8 }}>
          {actions.map((r) => <button key={r} className="btn" onClick={() => onReply(r)}>{r === "Done" && <Icon name="check" />}{r}</button>)}
          {soft.map((r) => <button key={r} className="btn soft" onClick={() => onReply(r)}>{r}</button>)}
        </div>
      </div>
    );
  }
  const toggle = (r) => setPicked((cur) => (cur.includes(r) ? cur.filter((x) => x !== r) : [...cur, r]));
  const chosen = answers.filter((r) => picked.includes(r));
  return (
    <div className="replies">
      <span className="caption">Pick every answer that applies, then send.</span>
      <div className="answers">
        {answers.map((r) => {
          const on = picked.includes(r);
          return (
            <button key={r} className={`answer ${on ? "on" : ""}`} aria-pressed={on} onClick={() => toggle(r)}>
              <Icon name={on ? "checkbox-marked-circle" : "checkbox-blank-circle-outline"} size={18} />{r}
            </button>
          );
        })}
      </div>
      <div className="row wrap" style={{ gap: 8 }}>
        <button className="btn" disabled={!chosen.length} onClick={() => onReply(chosen.join("; "), chosen)}>
          <Icon name="send" size={16} />{chosen.length > 1 ? `Send ${chosen.length} Answers` : "Send Answer"}
        </button>
        {soft.map((r) => <button key={r} className="btn soft" onClick={() => onReply(r)}>{r}</button>)}
      </div>
    </div>
  );
}

// The expert's summary beside the chat: the issue, findings so far, every file, similar cases
function IssueSummary({ sv, onLiveData }) {
  const s = sv.session;
  const rep = s.report || {};
  const esc = useAsync(() => (sv.escalation ? api.get(`/api/escalations/${sv.escalation.ticket}`) : Promise.resolve(null)),
                       [sv.escalation?.ticket]);
  const causes = (sv.fishbone || []).flatMap((b) => b.causes).sort((a, b) => (a.ruled_out - b.ruled_out) || b.likelihood - a.likelihood);
  const files = sv.messages.flatMap((m) => m.attachments || []);
  const seen = new Set();
  const uniq = files.filter((f) => (seen.has(f.id) ? false : seen.add(f.id)));
  const checks = (esc.data?.payload?.diagnostic_summary?.checkpoint_matrix || []).filter((c) => c.source !== "issue report");
  const note = esc.data?.payload?.operator_request?.description;
  const chatSummary = [...sv.messages].reverse().find((m) => m.type === "escalation")?.summary;
  return (
    <aside className="summary">
      <div className="row"><Icon name="clipboard-text-search-outline" size={20} color="var(--gps-primary)" /><div className="section-title grow">Issue Summary</div></div>

      {chatSummary && (
        <div className="card">
          <div className="card-title">Summary of the chat</div>
          <div style={{ color: "var(--t80)", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>{chatSummary}</div>
        </div>
      )}

      <div className="card">
        <div className="card-title">Reported issue</div>
        <div className="row" style={{ alignItems: "flex-start" }}>
          <Icon name={sv.equipment ? sv.icon : "map-marker-question-outline"} size={20} color="var(--t60)" />
          <div className="grow">
            <div style={{ color: "var(--t80)", fontWeight: 600 }}>{sv.equipment ? sv.equipment.name : "Equipment not identified yet"}</div>
            <div className="caption">{sv.area.name}{sv.equipment ? ` · ${sv.equipment.kind}${sv.equipment.tag ? ` · ${sv.equipment.tag}` : ""}` : ""}</div>
          </div>
          <span className="tag" style={{ background: URGENCY_BG[s.severity], color: "#fff" }}>{s.severity}</span>
        </div>
        {(rep.symptom_labels || []).length > 0 && (
          <div className="row wrap" style={{ gap: 6 }}>{rep.symptom_labels.map((x) => <span key={x} className="val-pill" style={{ background: "#fff7e6", color: "#b36b00" }}>{x}</span>)}</div>
        )}
        {rep.description && <div style={{ color: "var(--t70)", lineHeight: 1.5 }}>{rep.description}</div>}
        {note && <div className="note"><div className="overline">Note to the expert</div>{note}</div>}
        <div className="caption">{rep.project ? `${rep.project} · ` : ""}Reported by {rep.reported_by || "—"} · {fmtTime(rep.reported_at || s.created_at)}</div>
        <button className="btn ghost sm" style={{ alignSelf: "flex-start" }} onClick={onLiveData} disabled={!sv.telemetry}><Icon name="chart-line" />Plant Live Data</button>
      </div>

      <div className="card">
        <div className="card-title">Findings so far</div>
        {s.root_cause && <div className="note ok"><div className="overline">Root cause</div><b>{s.root_cause}</b></div>}
        {causes.length ? causes.slice(0, 6).map((c) => (
          <div key={c.label} className={`cause-row ${c.ruled_out ? "out" : ""}`}>
            <span className="cause-label">{c.label}</span>
            <span className="cause-pct">{c.ruled_out ? "ruled out" : `${Math.round(c.likelihood * 100)}%`}</span>
          </div>
        )) : <div className="caption">Causes are listed once the equipment is identified.</div>}
        {checks.length > 0 && (
          <details>
            <summary className="link-summary">Checks done · {checks.length}</summary>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, paddingTop: 6 }}>
              {checks.map((c) => <div key={c.checkpoint_id} className="caption" style={{ color: "var(--t70)", lineHeight: 1.45 }}>{c.description} <b>{c.operator_input}</b></div>)}
            </div>
          </details>
        )}
      </div>

      <div className="card">
        <div className="card-title">Photos, videos & files · {uniq.length}</div>
        {uniq.length ? <div className="row wrap" style={{ gap: 8 }}>{uniq.map((f) => <Attachment key={f.id} file={f} path={`/api/sessions/${s.id}/files/${f.id}`} />)}</div>
          : <div className="caption">Nothing attached yet.</div>}
        {uniq.filter((f) => f.analysis && !f.analysis.error).map((f) => <Reading key={f.id} a={f.analysis} name={f.filename} />)}
      </div>

      <div className="card">
        <div className="card-title">Similar past cases</div>
        {sv.cases.length ? <SimilarCases cases={sv.cases} /> : <div className="caption">No similar cases yet.</div>}
      </div>
    </aside>
  );
}

const TAG_LABEL = (t) => t.replace(/_/g, " ").replace(/\b(pct)\b/, "%").replace(/\b(c)$/, "°C").replace(/\bmm s\b/, "mm/s")
  .replace(/^\w/, (c) => c.toUpperCase());

function LiveDataModal({ sv, onClose }) {
  const tags = Object.entries(sv.telemetry?.tags || {});
  return (
    <Modal title={`Plant live data · ${sv.equipment?.name || sv.area.name}`} onClose={onClose} width={640}>
      <div className="safety"><Icon name="information-outline" /><div>Demo data: a simulated 30-minute trend. This connects to the plant SCADA in a later version.</div></div>
      {tags.map(([k, v]) => {
        const series = Array.isArray(v) ? v : null;
        return (
          <div key={k} className="rd-row">
            <span className="grow">{TAG_LABEL(k)}</span>
            {series && <Sparkline values={series} width={160} />}
            <b style={{ minWidth: 80, textAlign: "right" }}>{series ? series[series.length - 1] : v}</b>
          </div>
        );
      })}
      {!tags.length && <div className="caption">No live tags for this equipment.</div>}
    </Modal>
  );
}

function EscalateModal({ sid, busy, notify, onClose, onSubmit }) {
  const [description, setDescription] = useState("");
  const [summary, setSummary] = useState(null); // null while it is being written
  const media = useFiles(notify);
  useEffect(() => {
    api.get(`/api/sessions/${sid}/chat-summary`).then((r) => setSummary(r.summary)).catch(() => setSummary(""));
  }, [sid]);
  return (
    <Modal title="Escalate to a technical expert" onClose={onClose} width={600}>
      <div className="caption" style={{ lineHeight: 1.5 }}>
        The experts get an email with this summary, the chat, your checks and every photo, video and voice note. They reply
        here when they can — you don't need to wait on this screen, and you'll be notified when they reply.
      </div>
      <label className="field"><span className="overline">Summary of the chat for the expert · you can edit it</span>
        {summary === null ? <div className="caption"><Icon name="loading" className="spin" size={14} /> Summarising the chat…</div> : (
          <textarea className="textarea" rows={6} value={summary} onChange={(e) => setSummary(e.target.value)}
                    placeholder="What the problem is, what you checked and what you found" />
        )}
      </label>
      <label className="field"><span className="overline">Anything else the expert should know</span>
        <textarea className="textarea" rows={3} value={description} onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Knocking from the 2nd-stage valve since 10:00, gets worse under load; I topped up the oil but no change" /></label>
      <MediaButtons onFiles={media.add} onError={(m) => notify(m, true)} disabled={media.files.length >= MAX_FILES} />
      <FileChips files={media.files} onRemove={media.remove} />
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn danger" disabled={busy || summary === null || media.tooBig.length > 0}
                onClick={() => onSubmit({ description: description.trim(), summary: (summary || "").trim(), files: media.files })}>
          {busy ? "Sending…" : "Send To The Experts"}
        </button>
      </div>
    </Modal>
  );
}

// The reporter confirms before the issue is closed: closing ends the chat for good
function CloseModal({ busy, identified, withExpert, reply, onClose, onConfirm }) {
  const [note, setNote] = useState("");
  const askNote = !identified && !reply;
  return (
    <Modal title="Resolve and close this issue?" onClose={onClose} width={520}>
      <div className="close-summary">
        <Icon name={identified ? "check-decagram-outline" : "archive-check-outline"} size={22} color={identified ? "var(--gps-primary)" : "var(--t60)"} />
        <div style={{ lineHeight: 1.5 }}>
          {identified
            ? `The cause and fix${withExpert ? " from the expert" : ""} are saved to the knowledge base, so the next person gets there faster.`
            : "No cause has been confirmed, so the issue is saved as closed."}
        </div>
      </div>
      <div className="caption">The chat ends here. If the problem comes back, report a new issue.</div>
      {askNote && (
        <label className="field"><span className="overline">How was it fixed? · optional</span>
          <textarea className="textarea" rows={3} value={note} onChange={(e) => setNote(e.target.value)}
                    placeholder="e.g. Sensor cable was loose, re-terminated and readings are normal" /></label>
      )}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose} disabled={busy}>Keep Working On It</button>
        <button className="btn" disabled={busy} onClick={() => onConfirm(note.trim())}>
          <Icon name="check-circle-outline" />{busy ? "Closing…" : "Yes, Resolve & Close"}
        </button>
      </div>
    </Modal>
  );
}

function ResolutionModal({ busy, reporter, onClose, onSubmit }) {
  const [cause, setCause] = useState("");
  const [steps, setSteps] = useState("");
  const [note, setNote] = useState("");
  const lines = steps.split("\n").map((x) => x.trim()).filter(Boolean);
  return (
    <Modal title={`Share the resolution with ${reporter}`} onClose={onClose} width={600}>
      <div className="caption">They apply the steps and close the issue once it works. The cause and fix are saved to the knowledge base.</div>
      <input className="input" placeholder="Confirmed cause" value={cause} onChange={(e) => setCause(e.target.value)} />
      <textarea className="textarea" rows={4} placeholder="Steps to fix it, one per line" value={steps} onChange={(e) => setSteps(e.target.value)} />
      <textarea className="textarea" rows={2} placeholder="Message (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn" disabled={busy || !cause.trim() || !lines.length}
                onClick={() => onSubmit({ text: note.trim(), root_cause: cause.trim(), steps: lines })}>Send Resolution</button>
      </div>
    </Modal>
  );
}
