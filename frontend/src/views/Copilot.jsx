import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { Attachment, Empty, FILE_ICON, Icon, Modal, PillTabs, SEV, Spinner, URGENCY_BG, fmtSize, fmtTime, usePoll } from "../components/ui";
import { CAT_COLOR, CatChip, Fishbone, WhyChain } from "../components/rca";

const STAGES = [
  ["Issue Report", "clipboard-alert-outline"],
  ["Fishbone", "fish"],
  ["5-Why", "head-question-outline"],
  ["Resolution", "wrench-outline"],
  ["Expert Support", "account-hard-hat-outline"],
];
const EXPERT_STAGE = STAGES.length - 1;
// helper replies that steer the conversation rather than answer it
const SOFT_REPLIES = new Set(["How do I check this?", "I can't check this", "Not sure", "Skip to the fix",
                              "How do I do this?", "I can't do this step", "Show all steps", "No, still a problem"]);
// replies that end the chat: the field operator confirms them first
const CLOSING_REPLIES = new Set(["Yes, it's working normally", "No issue found, close session"]);
const TONE = { warn: ["#fff7e6", "#ffa500"], info: ["#e8f2fd", "#3191ef"], ok: ["#e3f2d4", "#006400"] };
const STATUS_LABEL = { active: ["In progress", "var(--gps-orange)"], escalated: ["With expert", "var(--gps-info)"],
                       resolved: ["Resolved", "var(--gps-green-mid)"], closed: ["Closed", "var(--t50)"] };
const MAX_FILES = 5;
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const FILE_TYPES = "image/*,video/*,audio/*,.pdf,.txt,.csv,.xlsx,.xls,.docx,.doc";

// The issue as reported (symptoms and description) — the title of an issue everywhere in the copilot
export const issueTitle = (symptom) => symptom || "Reported issue";

export default function Copilot({ meta, user, equipment, openIssues, params, notify, refreshShared }) {
  const canReport = user.role === "field_operator";
  const [listTab, setListTab] = useState("open");
  const [recent, setRecent] = useState(null);
  const [query, setQuery] = useState("");
  const [reporting, setReporting] = useState(null); // null, or the form prefill {areaId, equipmentId}
  const [sv, setSv] = useState(null);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [files, setFiles] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [override, setOverride] = useState(null);
  const [resolving, setResolving] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const [closing, setClosing] = useState(null); // null, or {reply} — the closing reply (or the button) to confirm
  const scrollRef = useRef(null);
  const isExpert = user.role === "expert";

  useEffect(() => {
    if (listTab === "recent") api.get("/api/sessions?limit=40").then(setRecent).catch((e) => notify(e.message, true));
  }, [listTab, notify]);

  const listed = useMemo(() => {
    const q = query.trim().toLowerCase();
    return ((listTab === "open" ? openIssues : recent) || [])
      .filter((r) => !q || `${r.id} ${r.eq_name} ${r.unit_name} ${r.project || ""} ${r.symptom || ""}`.toLowerCase().includes(q));
  }, [listTab, openIssues, recent, query]);

  const load = useCallback(async (fn) => {
    setBusy(true);
    try {
      const v = await fn();
      setSv(v);
      setReporting(null);
      return v;
    } catch (e) {
      notify(e.message, true);
      return null;
    } finally {
      setBusy(false);
    }
  }, [notify]);

  // initial view: a session from navigation, a prefilled report, else the report form (or the issue list)
  useEffect(() => {
    if (params.sessionId) load(() => api.get(`/api/sessions/${params.sessionId}`));
    else if (params.report || canReport) setReporting(params.report || {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const open = (sid) => {
    if (busy) return;
    load(() => api.get(`/api/sessions/${sid}`));
  };

  const submitReport = async (body) => {
    const v = await load(() => api.post("/api/sessions", body));
    if (v) {
      refreshShared();
      setListTab("open");
    }
  };

  const s = sv?.session;
  const resolved = s && ["resolved", "closed"].includes(s.status);
  const live = s && s.mode === "expert" && !resolved;
  usePoll(() => {
    if (s && !busy) api.get(`/api/sessions/${s.id}`).then((v) => v.messages.length !== sv.messages.length || v.session.status !== s.status ? setSv(v) : null).catch(() => {});
  }, live && !reporting ? 3000 : 0, [s?.id, live, busy, sv?.messages.length, reporting]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [sv?.messages.length, busy, reporting]);
  useEffect(() => setFiles([]), [s?.id]);

  const act = async (path, body) => {
    if (!s) return;
    const v = await load(() => api.post(`/api/sessions/${s.id}${path}`, body));
    if (v) refreshShared();
    return v;
  };

  // choices: the options picked together on a multi-select check (text is their readable form)
  const send = async (text, choices = []) => {
    text = (text || "").trim();
    if (!text || busy || !s) return;
    setInput("");
    if (isExpert && s.mode === "expert") return act("/expert-message", { text });
    setSv((cur) => ({ ...cur, messages: [...cur.messages, { id: "tmp", type: "user", text }] }));
    return act("/messages", { text, choices });
  };

  const addFiles = (list) => {
    const picked = Array.from(list || []);
    if (!picked.length) return;
    setFiles((cur) => {
      const next = [...cur, ...picked];
      if (next.length > MAX_FILES) notify(`Attach up to ${MAX_FILES} files at a time`, true);
      return next.slice(0, MAX_FILES);
    });
  };
  const tooBig = files.filter((f) => f.size > MAX_FILE_BYTES);

  // the composer: text, files, or both
  const submit = async () => {
    if (busy || !s) return;
    if (!files.length) return send(input);
    if (tooBig.length) return notify(`${tooBig.map((f) => f.name).join(", ")} is over 10 MB`, true);
    const text = input.trim();
    const fd = new FormData();
    fd.append("text", text);
    files.forEach((f) => fd.append("files", f));
    setInput("");
    const v = await act("/files", fd);
    if (v) setFiles([]);
    else setInput(text);
  };

  const reply = (text, choices) => {
    if (!CLOSING_REPLIES.has(text)) return send(text, choices);
    if (!canReport) return notify("Only the field operator can close the issue", true);
    setClosing({ reply: text });
  };

  const confirmClose = async (note) => {
    const v = closing.reply ? await send(closing.reply) : await act("/resolve", { note });
    if (v) setClosing(null);
  };

  const escalate = async ({ description, files }) => {
    const fd = new FormData();
    fd.append("description", description);
    files.forEach((f) => fd.append("files", f));
    const v = await act("/escalate", fd);
    if (v) setEscalating(false);
  };

  const shareResolution = async (body) => {
    const v = await act("/expert-message", body);
    if (v) setResolving(false);
  };

  const requestOverride = async (reason) => {
    try {
      const o = await api.post("/api/control/overrides", { interlock_id: override.id, reason });
      notify(o.status === "blocked" ? `Override blocked: ${o.decision_note}` : "Override request sent to the control room", o.status === "blocked");
      setOverride(null);
    } catch (e) {
      notify(e.message, true);
    }
  };

  // quick replies belong to the latest prompt until the field operator answers (events don't count)
  const replyIdx = (() => {
    if (!sv) return -1;
    for (let i = sv.messages.length - 1; i >= 0; i--) {
      const m = sv.messages[i];
      if (m.type === "user" || m.type === "solution") return -1;
      if (m.replies?.length) return i;
    }
    return -1;
  })();
  const withExpert = s?.mode === "expert";
  const expertJoined = withExpert && !!sv.escalation?.claimed_by;
  const stageIdx = sv?.stage.index ?? 0;
  const chatOpen = !!sv && !reporting;
  // the newest fishbone card in the chat follows the answers live; older ones show how it looked then
  const lastFishbone = sv ? sv.messages.map((m) => m.type).lastIndexOf("fishbone") : -1;
  const canSend = !busy && !resolved && (input.trim() || files.length) && !tooBig.length;

  return (
    <div className="copilot">
      {!chatOpen && (
        <section className="eq-col col-h">
          {canReport && (
            <button className="btn" onClick={() => setReporting({})} disabled={busy}>
              <Icon name="clipboard-alert-outline" /> Report An Issue
            </button>
          )}
          <PillTabs stretch value={listTab} onChange={setListTab}
                    options={[["open", `Open Issues (${openIssues.length})`], ["recent", "Recent"]]} />
          <div className="search">
            <Icon name="magnify" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find an issue" aria-label="Find an issue" />
          </div>
          <div className="eq-list">
            {listTab === "recent" && !recent ? <Spinner /> : listed.map((r) => {
              const [label, color] = STATUS_LABEL[r.status] || [r.status, "var(--t60)"];
              return (
                <button key={r.id} className="eq-item issue-item" onClick={() => open(r.id)}>
                  <Icon name={r.area_level ? "map-marker-question-outline" : r.icon} />
                  <div className="grow" style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
                    <span className="issue-title" title={issueTitle(r.symptom)}>{issueTitle(r.symptom)}</span>
                    <span className="caption ellipsis">
                      <b style={{ color: "var(--t70)" }}>{r.area_level ? "Equipment not identified" : r.eq_name}</b> · {r.unit_name}
                    </span>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                    <span className="tag" style={{ background: URGENCY_BG[r.severity], color: "#fff" }}>{r.severity}</span>
                    <span className="status-text" style={{ color }}>{label}</span>
                  </div>
                </button>
              );
            })}
            {listTab === "open" && !listed.length && (
              <Empty title="No Open Issues">{canReport ? "Report an issue when you notice something abnormal in the field." : "Nothing is being troubleshot right now."}</Empty>
            )}
          </div>
        </section>
      )}

      <section className={`chat col-h ${dragging ? "dragging" : ""}`}
               onDragOver={(e) => { if (chatOpen && !resolved && e.dataTransfer.types.includes("Files")) { e.preventDefault(); setDragging(true); } }}
               onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false); }}
               onDrop={(e) => { if (!chatOpen || resolved) return; e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}>
        {reporting ? (
          <ReportForm meta={meta} equipment={equipment} prefill={reporting} busy={busy} onSubmit={submitReport}
                      onOpen={open} onCancel={sv ? () => setReporting(null) : null} />
        ) : !sv ? (
          busy ? <Spinner text="Opening session…" /> : <Empty icon="message-processing-outline" title="Select an issue">Pick an issue on the left to see its troubleshooting chat.</Empty>
        ) : (
          <>
            <div className="chat-head">
              <button className="btn ghost sm" onClick={() => setSv(null)} title="Back to the issue list" aria-label="Back to the issue list">
                <Icon name="arrow-left" />
              </button>
              <div style={{ flex: "1 1 200px", minWidth: 0 }}>
                <div className="section-title issue-head" title={issueTitle(s.symptom)}>{issueTitle(s.symptom)}</div>
                <div className="caption">
                  <b style={{ color: "var(--t80)" }}>{sv.equipment ? sv.equipment.name : "Equipment not identified yet"}</b>
                  {" · "}{sv.area.name} · {s.id}{s.report?.project ? ` · ${s.report.project}` : ""}
                </div>
                <div className="caption">
                  {s.mode === "expert"
                    ? isExpert ? `Chat with ${s.report?.reported_by || "the field operator"}`
                      : expertJoined ? `Chat with ${sv.escalation.expert_name} (${sv.escalation.expert_role})`
                      : `Waiting for a ${sv.escalation?.expert_role || "technical expert"} to join`
                    : `${sv.equipment?.kind || "Area report"} · ${s.engine === "llm" ? `${sv.llm.label || "LLM"} knowledge engine` : "Decision-tree knowledge engine"}`}
                  {" · "}severity {s.severity}
                </div>
              </div>
              {resolved && <span className="status-text" style={{ color: STATUS_LABEL[s.status][1] }}>{STATUS_LABEL[s.status][0]}</span>}
              {canReport && !resolved && (
                <button className="btn outline sm" disabled={busy} title="Mark the issue resolved and close the chat"
                        onClick={() => setClosing({})}><Icon name="check-circle-outline" />Resolve & Close</button>
              )}
              {isExpert && s.mode === "expert" && !resolved && (
                <button className="btn outline sm" disabled={busy} title="Send the confirmed root cause and the steps to fix it"
                        onClick={() => setResolving(true)}><Icon name="check-decagram-outline" />Share Resolution</button>
              )}
              {s.mode !== "expert" && !resolved && (
                <button className="btn outline-danger sm" disabled={busy} onClick={() => setEscalating(true)}>Escalate To Expert</button>
              )}
            </div>

            <div className="stages">
              {STAGES.map(([label, icon], i) => {
                const isExp = i === EXPERT_STAGE;
                const active = isExp ? s.mode === "expert" && !resolved : i === stageIdx && !resolved;
                const done = isExp ? s.mode === "expert" && resolved : i < stageIdx || (resolved && i <= stageIdx);
                return (
                  <div key={label} className={`stage ${done ? "done" : active ? "active" : ""}`}>
                    <span className="stage-dot"><Icon name={done ? "check" : icon} /></span>
                    <span>{label}</span>
                    {i < EXPERT_STAGE && <span className="stage-line" />}
                  </div>
                );
              })}
              <span className="caption" style={{ marginLeft: "auto" }}>
                {sv.localizing ? "locating equipment" : sv.phase === "why" ? `why #${(sv.rca?.chain?.length || 0) + 1}`
                  : `${sv.checks} check${sv.checks === 1 ? "" : "s"} answered · confidence ${Math.round(s.confidence * 100)}%`}
              </span>
            </div>

            <div className="msgs" ref={scrollRef}>
              {sv.messages.map((m, i) => (
                <Message key={m.id + "-" + i} m={m} sid={s.id}
                  showReplies={i === replyIdx && !busy && !resolved && !withExpert}
                  onReply={reply}
                  live={i === lastFishbone ? { bones: sv.fishbone, checks: sv.checks } : null}
                  surveyOpen={m.type === "survey" && !!sv.survey && !resolved && !withExpert && !isExpert}
                  onSurvey={(body) => act("/survey", body)} busy={busy}
                  onEscalate={() => setEscalating(true)} mode={s.mode} />
              ))}
              {busy && (
                <div className="row" style={{ color: "var(--t50)", paddingLeft: 38 }}>
                  <Icon name="loading" className="spin" size={20} color="var(--gps-primary)" />
                  <span>{withExpert ? "Sending…" : "SiteBrain is thinking…"}</span>
                </div>
              )}
            </div>

            {files.length > 0 && (
              <div className="composer-files">
                {files.map((f, i) => (
                  <span key={`${f.name}-${i}`} className={`file-chip ${f.size > MAX_FILE_BYTES ? "bad" : ""}`}
                        title={f.size > MAX_FILE_BYTES ? "Over 10 MB — remove it to send" : f.name}>
                    <Icon name={FILE_ICON(f.type || "", f.name)} size={16} />
                    <span className="file-chip-name">{f.name}</span>
                    <span className="caption">{fmtSize(f.size)}</span>
                    <button aria-label={`Remove ${f.name}`} onClick={() => setFiles((cur) => cur.filter((_, j) => j !== i))}>
                      <Icon name="close" size={14} />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="composer">
              <label className={`btn ghost attach-btn ${resolved || files.length >= MAX_FILES ? "disabled" : ""}`}
                     title="Attach photos, PDFs, spreadsheets or other files (up to 5, 10 MB each)">
                <Icon name="paperclip" size={20} />
                <input type="file" multiple hidden accept={FILE_TYPES} disabled={resolved || files.length >= MAX_FILES}
                       aria-label="Attach files" onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }} />
              </label>
              <textarea rows={2} value={input} disabled={resolved}
                placeholder={resolved ? "Issue closed — report a new issue if it comes back"
                  : files.length ? "Add a message about the files (optional)"
                  : sv.survey && !withExpert ? "Fill in the condition checks above, or ask me anything"
                  : sv.phase === "fix" ? "Tap Done when finished, or ask me anything about this step"
                  : isExpert && withExpert ? `Reply to ${s.report?.reported_by || "the field operator"}`
                  : withExpert ? (expertJoined ? `Message ${sv.escalation.expert_name}` : "Message the expert — they'll see it when they join")
                  : sv.localizing ? "Name the equipment showing the problem, or say Not sure"
                  : sv.phase === "why" ? "Pick the closest answer, or explain in your own words why it happened"
                  : "Tap an answer (or several), or tell me in your own words what you see"}
                onChange={(e) => setInput(e.target.value)}
                onPaste={(e) => { if (e.clipboardData.files.length) { e.preventDefault(); addFiles(e.clipboardData.files); } }}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canSend) submit(); } }} />
              <button className="btn" style={{ padding: "12px 20px" }} onClick={submit} disabled={!canSend}>Send</button>
            </div>
            {dragging && <div className="drop-hint"><Icon name="tray-arrow-down" size={28} />Drop files to attach them</div>}
          </>
        )}
      </section>

      {chatOpen && <EnginePanel sv={sv} onOverride={setOverride} />}

      {override && <OverrideModal interlock={override} onClose={() => setOverride(null)} onSubmit={requestOverride} />}
      {escalating && <EscalateModal busy={busy} onClose={() => setEscalating(false)} onSubmit={escalate} />}
      {resolving && <ResolutionModal busy={busy} onClose={() => setResolving(false)} onSubmit={shareResolution} />}
      {closing && <CloseModal busy={busy} identified={!!s?.identified} withExpert={withExpert} reply={closing.reply}
                              onClose={() => setClosing(null)} onConfirm={confirmClose} />}
    </div>
  );
}

const timeOf = (iso) => (iso ? new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : "");

const SEV_TONE = { Low: "var(--t50)", Medium: "#3191ef", High: "#ffa500", Critical: "#f5524a" };

function ReportForm({ meta, equipment, prefill, busy, onSubmit, onOpen, onCancel }) {
  const [projects, setProjects] = useState(null);
  const [projectId, setProjectId] = useState("");
  const [areas, setAreas] = useState(null);
  const [areaId, setAreaId] = useState(prefill.areaId || "");
  const [eqId, setEqId] = useState(prefill.equipmentId || "");
  const [symptoms, setSymptoms] = useState([]);
  const [severity, setSeverity] = useState("Medium");
  const [description, setDescription] = useState("");

  useEffect(() => {
    api.get("/api/areas").then(setAreas).catch(() => setAreas([]));
    api.get("/api/projects").then(setProjects).catch(() => setProjects([]));
  }, []);
  useEffect(() => {
    if (prefill.equipmentId && !prefill.areaId) {
      const e = equipment.find((x) => x.id === prefill.equipmentId);
      if (e) setAreaId(e.area_id);
    }
  }, [prefill, equipment]);

  const areaEq = equipment.filter((e) => String(e.area_id) === String(areaId));
  const chosen = equipment.find((e) => e.id === eqId);
  // symptoms the chosen equipment (or any equipment in the chosen area) can show
  const kinds = new Set(chosen ? [chosen.kind] : areaEq.map((e) => e.kind));
  const fitting = !areaId ? [] : meta.symptoms.filter((sy) => !kinds.size || sy.kinds.some((k) => kinds.has(k)));
  const fitKey = fitting.map((sy) => sy.id).join();
  useEffect(() => {
    setSymptoms((cur) => cur.filter((id) => fitting.some((sy) => sy.id === id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey]);
  const toggle = (id) => setSymptoms((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  const ready = projectId && areaId && (symptoms.length || description.trim());

  return (
    <>
      <div className="chat-head">
        <div style={{ flex: "1 1 200px", minWidth: 0 }}>
          <div className="section-title">Report An Issue</div>
          <div className="caption">Tell SiteBrain where the problem is and what you notice. It will ask field checks to find the cause.</div>
        </div>
        {onCancel && <button className="btn ghost sm" onClick={onCancel}>Cancel</button>}
      </div>
      <div className="msgs" style={{ background: "var(--white)", gap: 20 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="overline">Project</div>
          {!projects ? <Spinner /> : (
            <select className="select" value={projectId} aria-label="Project"
                    onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Select the project…</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}{p.name !== p.code ? ` (${p.code})` : ""}</option>)}
            </select>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="overline">Where · area</div>
          {!areas ? <Spinner /> : (
            <select className="select" value={areaId} aria-label="Area"
                    onChange={(e) => { setAreaId(e.target.value ? Number(e.target.value) : ""); setEqId(""); }}>
              <option value="">Select the area…</option>
              {areas.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.code})</option>)}
            </select>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="overline">Equipment · optional</div>
          <select className="select" value={eqId} disabled={!areaId} aria-label="Equipment" onChange={(e) => setEqId(e.target.value)}>
            <option value="">Not sure / whole area — SiteBrain will help find it</option>
            {areaEq.map((e) => <option key={e.id} value={e.id}>{e.name} · {e.kind}{e.tag ? ` · ${e.tag}` : ""}</option>)}
          </select>
          {chosen?.open_session_id && (
            <div className="safety" style={{ alignItems: "center" }}>
              <Icon name="information-outline" />
              <div className="grow">{chosen.name} already has an open issue ({chosen.open_session_id}).</div>
              <button className="btn ghost sm" onClick={() => onOpen(chosen.open_session_id)}>Open It</button>
            </div>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="overline">What do you notice</div>
          {!areaId && <div className="caption">Pick the area (and equipment, if you know it) to see what you can report.</div>}
          <div className="row wrap" style={{ gap: 8 }}>
            {fitting.map((sy) => {
              const on = symptoms.includes(sy.id);
              return (
                <button key={sy.id} className="opt" aria-pressed={on} onClick={() => toggle(sy.id)}
                        style={on ? { background: "var(--gps-primary-lgt)", color: "var(--gps-green-dark)", borderColor: "var(--gps-primary)", fontWeight: 600 } : undefined}>
                  <Icon name={sy.icon} /> {sy.label}
                </button>
              );
            })}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="overline">How serious</div>
          <div className="row wrap" style={{ gap: 8 }}>
            {meta.severities.map((sv) => (
              <button key={sv} className="opt" aria-pressed={severity === sv} onClick={() => setSeverity(sv)}
                      style={severity === sv ? { background: SEV_TONE[sv], color: "#fff", borderColor: SEV_TONE[sv], fontWeight: 600 } : undefined}>
                {sv}
              </button>
            ))}
          </div>
          <div className="caption">Critical: stop-the-plant risk (heavy vibration, gas leak, smoke).</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="overline">Describe it</div>
          <textarea className="textarea" rows={3} value={description} onChange={(e) => setDescription(e.target.value)}
                    placeholder="What, where and since when — e.g. grinding noise at the gearbox since the start of shift" />
        </div>
      </div>
      <div className="composer" style={{ justifyContent: "flex-end" }}>
        <span className="caption grow">{!projectId ? "Pick the project." : !areaId ? "Pick the area first."
          : !ready ? "Pick a symptom or describe the issue." : ""}</span>
        <button className="btn" disabled={!ready || busy}
                onClick={() => onSubmit({ project_id: projectId, area_id: areaId, equipment_id: eqId || null, symptoms, severity, description })}>
          {busy ? "Starting…" : "Start Troubleshooting"}
        </button>
      </div>
    </>
  );
}

function Files({ sid, files }) {
  return (
    <div className="row wrap" style={{ gap: 8 }}>
      {files.map((f) => <Attachment key={f.id} file={f} path={`/api/sessions/${sid}/files/${f.id}`} />)}
    </div>
  );
}

function Message({ m, sid, showReplies, onReply, onEscalate, mode, live, surveyOpen, onSurvey, busy }) {
  const replies = m.replies || [];
  if (m.type === "survey") return <Survey m={m} open={surveyOpen} busy={busy} onSubmit={onSurvey} />;
  if (m.type === "user") {
    const files = m.attachments || [];
    return (
      <div className="msg" style={{ alignItems: "flex-end" }}>
        {m.survey ? (
          <div className="bubble-user" style={{ whiteSpace: "normal", minWidth: 260 }}>
            <div className="overline" style={{ marginBottom: 6 }}>Present condition</div>
            {m.survey.map((x, j) => (
              <div key={j} className="survey-answer"><span className="caption">{x.q}</span><b>{x.a}</b></div>
            ))}
          </div>
        ) : m.text && <div className="bubble-user">{m.text}</div>}
        {files.length > 0 && <div style={{ alignSelf: "flex-end" }}><Files sid={sid} files={files} /></div>}
        <span className="msg-time">{m.author || "You"}{m.created_at ? ` · ${timeOf(m.created_at)}` : ""}</span>
      </div>
    );
  }
  if (m.type === "report") {
    return (
      <div className="msg">
        <div className="bubble-user" style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 240 }}>
          <div className="overline">Issue reported{m.author ? ` by ${m.author}` : ""} · {m.project ? `${m.project} · ` : ""}{m.equipment || m.area}</div>
          <div className="row wrap" style={{ gap: 6 }}>
            {(m.symptoms || []).map((x) => <span key={x} className="tag" style={{ background: "var(--white)", color: "var(--t80)" }}>{x}</span>)}
            {m.severity && <span className="tag" style={{ background: URGENCY_BG[m.severity], color: "#fff" }}>{m.severity}</span>}
          </div>
          {m.description && <div>{m.description}</div>}
        </div>
      </div>
    );
  }
  if (m.type === "escalation") {
    return (
      <div className="msg" style={{ alignItems: "flex-end" }}>
        <div className="bubble-user" style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 240 }}>
          <div className="overline">Escalated to expert · {m.ticket}</div>
          {m.text ? <div>{m.text}</div> : <div className="caption">No description given.</div>}
          {(m.attachments || []).length > 0 && (
            <div className="row wrap" style={{ gap: 8 }}>
              {m.attachments.map((f) => <Attachment key={f.id} file={f} path={`/api/sessions/${sid}/files/${f.id}`} />)}
            </div>
          )}
        </div>
        <span className="msg-time">{m.author}{m.created_at ? ` · ${timeOf(m.created_at)}` : ""}</span>
      </div>
    );
  }
  if (m.type === "event") {
    const [bg, fg] = TONE[m.tone] || ["#f2f2f2", "#6d6d6d"];
    return (
      <div className="msg">
        <div className="event"><span className="line" />
          <div className="pillx" style={{ background: bg }}><Icon name={m.icon} size={16} color={fg} /><span>{m.text}</span></div>
          <span className="line" />
        </div>
      </div>
    );
  }
  if (m.type === "offer") {
    return mode === "expert" ? null : (
      <div className="msg"><div className="offer">
        <div style={{ lineHeight: 1.5 }}>{m.text}</div>
        <div><button className="btn danger" onClick={onEscalate}>Escalate To Technical Expert</button></div>
      </div></div>
    );
  }
  if (m.type === "signoff") return null; // safety sign-off was retired; older sessions may still hold one

  const expert = !!m.expert;
  const avatar = (icon) => (
    <div className={`avatar ${expert ? "expert" : ""}`}><Icon name={expert ? "account-hard-hat-outline" : icon} /></div>
  );
  return (
    <div className="msg">
      {m.type === "agent" && (
        <div className="agent-row">
          {avatar("robot-outline")}
          <div className="agent-body">
            <div className="caption">{m.who || "SiteBrain"} · {timeOf(m.created_at)}</div>
            {(m.text || m.items?.length > 0 || (!m.side && (m.why_step || m.fix_step))) && <div className={`bubble-agent ${expert ? "expert" : ""}`}>
              {!m.side && m.why_step && <span className="tag" style={{ background: "#e8f2fd", color: "#1c6fc1", marginRight: 8 }}>Why #{m.why_step}</span>}
              {!m.side && m.fix_step && <span className="tag" style={{ background: "var(--gps-primary-lgt)", color: "var(--gps-green-dark)", marginRight: 8 }}>Step {m.fix_step} of {m.fix_total}</span>}
              {m.text}
              {(m.items || []).length > 0 && (
                <ul style={{ margin: "6px 0 0", paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4 }}>
                  {m.items.map((x, j) => <li key={j} style={{ lineHeight: 1.45 }}>{x}</li>)}
                </ul>
              )}
            </div>}
            {(m.attachments || []).length > 0 && <Files sid={sid} files={m.attachments} />}
            {m.side && m.prompt && showReplies && (
              <div className="purpose"><Icon name="arrow-u-left-top" size={14} />
                <span>Back to {m.fix_step ? `step ${m.fix_step} of ${m.fix_total}` : m.why_step ? `why #${m.why_step}` : "the check"}: {m.prompt}</span></div>
            )}
            {!m.side && m.purpose && <div className="purpose"><Icon name="lightbulb-on-outline" size={14} /><span>Why I'm asking: {m.purpose}</span></div>}
            {m.safety && <div className="safety"><Icon name="shield-alert-outline" /><div><b>Safety · </b>{m.safety}</div></div>}
          </div>
        </div>
      )}
      {m.type === "fishbone" && (
        <div className="agent-row">
          {avatar("robot-outline")}
          <div className="agent-body wide">
            <div className="caption">
              SiteBrain · {m.updated ? "Updated fishbone" : "Possible causes (fishbone, 6M)"}
              {live ? <span className="live-tag"><span className="dot live" />live · {live.checks ? `after ${live.checks} check${live.checks === 1 ? "" : "s"}` : "updates as you answer"}</span>
                : m.updated ? ` · ${m.updated}` : " · at the start"}
            </div>
            <div className="panel"><Fishbone bones={live?.bones?.length ? live.bones : m.bones} problem={m.problem} max={3} /></div>
          </div>
        </div>
      )}
      {m.type === "finding" && (
        <div className="agent-row">
          <div className={`avatar ${expert ? "expert" : ""}`}><Icon name="magnify-scan" /></div>
          <div className="agent-body wide">
            <div className="caption">{m.who} · Direct cause found</div>
            <div className="panel" style={{ borderColor: "#ffa500" }}>
              <div className="row wrap" style={{ gap: 8 }}>
                <span style={{ fontSize: 16, fontWeight: 600 }}>{m.direct_cause}</span>
                <CatChip category={m.category} />
                {m.confidence != null && <span className="caption" style={{ marginLeft: "auto" }}>{Math.round(m.confidence * 100)}% confident</span>}
              </div>
              {m.safety && <div className="safety"><Icon name="shield-alert-outline" /><div><b>Keep it safe · </b>{m.safety}</div></div>}
            </div>
          </div>
        </div>
      )}
      {m.type === "analysis" && (
        <div className="agent-row">
          {avatar("robot-outline")}
          <div className="agent-body wide">
            <div className="caption">SiteBrain · {timeOf(m.created_at)}</div>
            <div className="panel">
              <div style={{ lineHeight: 1.5 }}>{m.text}</div>
              {(m.safety_rules || []).map((r) => (
                <div key={r} className="safety"><Icon name="shield-alert-outline" /><div><b>Safety · </b>{r}</div></div>
              ))}
              {m.footnote && <div className="caption" style={{ color: "var(--t60)" }}>{m.footnote}</div>}
            </div>
          </div>
        </div>
      )}
      {m.type === "solution" && (
        <div className="agent-row">
          <div className={`avatar ${expert ? "expert" : ""}`}><Icon name="check-decagram-outline" /></div>
          <div className="agent-body wide">
            <div className="caption">{m.who} · {m.text || "Root cause"}</div>
            <div className="panel solution" style={{ gap: 8 }}>
              <div className="row wrap" style={{ gap: 8, alignItems: "baseline" }}>
                <span className="overline">Root cause</span>{m.category && <CatChip category={m.category} />}
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.4 }}>{m.root_cause}</div>
              {m.direct_cause && m.direct_cause !== m.root_cause && (
                <div className="caption" style={{ color: "var(--t70)" }}>What failed: {m.direct_cause}</div>
              )}
              {(m.why_chain || []).length > 0 && (
                <details>
                  <summary className="caption" style={{ cursor: "pointer", color: "#1c6fc1", fontWeight: 600 }}>How we got here · {m.why_chain.length}-step why chain</summary>
                  <div style={{ paddingTop: 8 }}><WhyChain direct={m.direct_cause} chain={m.why_chain} root={m.root_cause} category={m.category} /></div>
                </details>
              )}
              {(m.preventive || []).length > 0 && (
                <details>
                  <summary className="caption" style={{ cursor: "pointer", color: "#1c6fc1", fontWeight: 600 }}>Preventive actions · {m.preventive.length}</summary>
                  <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>{m.preventive.map((x, j) => <li key={j} className="caption" style={{ color: "var(--t70)", lineHeight: 1.5 }}>{x}</li>)}</ul>
                </details>
              )}
              {m.basis && <div className="caption" style={{ color: "var(--t50)" }}>Based on {m.basis}</div>}
            </div>
          </div>
        </div>
      )}
      {showReplies && replies.length > 0 && <Replies replies={replies} multi={!!m.multi} onReply={onReply} />}
    </div>
  );
}

// The present-condition checks: several field checks answered together in one form
function Survey({ m, open, busy, onSubmit }) {
  const [picked, setPicked] = useState({}); // check id → options seen
  const [cant, setCant] = useState({});
  const toggle = (qid, o) => {
    setCant((c) => ({ ...c, [qid]: false }));
    setPicked((p) => { const cur = p[qid] || []; return { ...p, [qid]: cur.includes(o) ? cur.filter((x) => x !== o) : [...cur, o] }; });
  };
  const skip = (qid) => { setCant((c) => ({ ...c, [qid]: !c[qid] })); setPicked((p) => ({ ...p, [qid]: [] })); };
  const answered = m.questions.filter((q) => (picked[q.id] || []).length || cant[q.id]).length;
  const submit = () => onSubmit({
    answers: Object.fromEntries(m.questions.filter((q) => (picked[q.id] || []).length).map((q) => [q.id, picked[q.id]])),
    skipped: m.questions.filter((q) => cant[q.id]).map((q) => q.id),
  });
  return (
    <div className="msg">
      <div className="agent-row">
        <div className="avatar"><Icon name="clipboard-list-outline" /></div>
        <div className="agent-body wide">
          <div className="caption">SiteBrain · Present-condition check{open ? "" : " · answered"}</div>
          <div className="panel survey">
            <div style={{ lineHeight: 1.5 }}>{m.text}</div>
            {m.questions.map((q, n) => (
              <div key={q.id} className={`survey-q ${(picked[q.id] || []).length || cant[q.id] ? "done" : ""}`}>
                <div className="row" style={{ alignItems: "flex-start", gap: 8 }}>
                  <span className="step-n">{n + 1}</span>
                  <div className="grow" style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <div style={{ fontWeight: 600, color: "var(--t90)", lineHeight: 1.4 }}>{q.text}</div>
                    {q.purpose && <div className="caption"><Icon name="lightbulb-on-outline" size={13} /> {q.purpose}</div>}
                    {q.how && open && (
                      <details><summary className="caption" style={{ cursor: "pointer", color: "#1c6fc1", fontWeight: 600 }}>How do I check this?</summary>
                        <div className="caption" style={{ color: "var(--t70)", paddingTop: 4, lineHeight: 1.5 }}>{q.how}</div></details>
                    )}
                  </div>
                </div>
                {open && (
                  <div className="row wrap" style={{ gap: 6, paddingLeft: 30 }}>
                    {q.options.map((o) => {
                      const on = (picked[q.id] || []).includes(o);
                      return (
                        <button key={o} className={`btn sm ${on ? "" : "outline"}`} aria-pressed={on} disabled={busy} onClick={() => toggle(q.id, o)}>
                          <Icon name={on ? "checkbox-marked-outline" : "checkbox-blank-outline"} size={15} />{o}
                        </button>
                      );
                    })}
                    <button className={`btn sm ${cant[q.id] ? "" : "soft"}`} aria-pressed={!!cant[q.id]} disabled={busy}
                            style={cant[q.id] ? { background: "var(--t50)" } : undefined} onClick={() => skip(q.id)}>I can't check this</button>
                  </div>
                )}
              </div>
            ))}
            {open && (
              <div className="row wrap" style={{ gap: 8 }}>
                <button className="btn" disabled={busy || !answered} onClick={submit}>
                  <Icon name="send-outline" size={16} />{answered ? `Submit ${answered} of ${m.questions.length}` : "Submit"}
                </button>
                <button className="btn soft" disabled={busy} onClick={() => onSubmit({})}>Ask me one at a time</button>
                <span className="caption">Checks you leave blank may come up later.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Quick replies. On a multi-select check the answers toggle and are sent together; helper replies send at once.
function Replies({ replies, multi, onReply }) {
  const [picked, setPicked] = useState([]);
  const answers = replies.filter((r) => !SOFT_REPLIES.has(r));
  if (!multi || answers.length < 2) {
    return (
      <div className="replies">
        {replies.map((r) => <button key={r} className={`btn ${SOFT_REPLIES.has(r) ? "soft" : "outline"}`} onClick={() => onReply(r)}>{r}</button>)}
      </div>
    );
  }
  const toggle = (r) => setPicked((cur) => (cur.includes(r) ? cur.filter((x) => x !== r) : [...cur, r]));
  const chosen = answers.filter((r) => picked.includes(r)); // keep the order they were offered in
  return (
    <div className="replies" style={{ flexDirection: "column", alignItems: "flex-start" }}>
      <span className="caption">Pick every answer that applies, then send.</span>
      <div className="row wrap" style={{ gap: 8 }}>
        {answers.map((r) => {
          const on = picked.includes(r);
          return (
            <button key={r} className={`btn ${on ? "" : "outline"}`} aria-pressed={on} onClick={() => toggle(r)}>
              <Icon name={on ? "checkbox-marked-outline" : "checkbox-blank-outline"} size={16} />{r}
            </button>
          );
        })}
      </div>
      <div className="row wrap" style={{ gap: 8 }}>
        <button className="btn" disabled={!chosen.length} onClick={() => onReply(chosen.join("; "), chosen)}>
          <Icon name="send-outline" size={16} />{chosen.length > 1 ? `Send ${chosen.length} Answers` : "Send Answer"}
        </button>
        {replies.filter((r) => SOFT_REPLIES.has(r)).map((r) => <button key={r} className="btn soft" onClick={() => onReply(r)}>{r}</button>)}
      </div>
    </div>
  );
}

function EnginePanel({ sv, onOverride }) {
  const s = sv.session;
  const rep = s.report || {};
  const causes = [...(s.causes || [])].sort((a, b) => b.likelihood - a.likelihood).slice(0, 4);
  return (
    <section className="engine col-h">
      <div className="row"><Icon name="brain" size={20} color="var(--gps-primary)" /><div className="section-title">Knowledge Engine</div></div>

      {sv.interlocks.length > 0 && (
        <div className="card">
          <div className="card-title">Safety Interlocks</div>
          {sv.interlocks.map((i) => (
            <div key={i.id} className={`safety ${i.category === "interlock" ? "critical" : ""}`}>
              <Icon name={i.category === "interlock" ? "shield-lock-outline" : "shield-alert-outline"} />
              <div style={{ flex: 1 }}>
                <div><b>{i.rule_id}</b> · {i.action}</div>
                <div className="caption">{i.category} · {i.status}</div>
              </div>
              {i.category === "interlock" && (
                <button className="btn ghost sm" title="Request a bypass override" onClick={() => onOverride(i)}><Icon name="lock-open-outline" /></button>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="card" style={{ gap: 10 }}>
        <div className="card-title">Reported Issue</div>
        <div className="row" style={{ alignItems: "flex-start" }}>
          <Icon name={sv.equipment ? sv.icon : "map-marker-question-outline"} size={20} color="var(--t60)" />
          <div className="grow">
            <div style={{ color: "var(--t80)", fontWeight: 600 }}>{sv.equipment ? sv.equipment.name : "Equipment not identified yet"}</div>
            <div className="caption">{sv.area.name}{sv.equipment ? ` · ${sv.equipment.kind}${sv.equipment.tag ? ` · ${sv.equipment.tag}` : ""}` : ""}</div>
          </div>
          {rep.severity && <span className="tag" style={{ background: URGENCY_BG[rep.severity], color: "#fff" }}>{rep.severity}</span>}
        </div>
        {(rep.symptom_labels || []).length > 0 && (
          <div className="row wrap" style={{ gap: 6 }}>
            {rep.symptom_labels.map((x) => <span key={x} className="val-pill" style={{ background: SEV.warn[0], color: SEV.warn[1] }}>{x}</span>)}
          </div>
        )}
        {rep.description && <div style={{ color: "var(--t70)", lineHeight: 1.5 }}>{rep.description}</div>}
        <div className="caption">{rep.project ? `Project ${rep.project} · ` : ""}Reported by {rep.reported_by || "—"} · {fmtTime(rep.reported_at || s.created_at)}</div>
      </div>

      <div className="card" style={{ gap: 12 }}>
        <div className="row"><Icon name="fish" size={18} color="var(--t60)" /><div className="card-title grow">Fishbone · 6M</div>
          {causes[0] && <span className="caption">lead {Math.round(causes[0].likelihood * 100)}%</span>}</div>
        {sv.fishbone?.length ? (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {sv.fishbone.map((b) => (
              <div key={b.category} className="fb-bone" style={{ "--fb": CAT_COLOR[b.category] }}>
                <div className="fb-cat">{b.label}</div>
                {b.causes.slice(0, 3).map((c) => (
                  <div key={c.label} className={`fb-cause ${c.ruled_out ? "out" : causes[0]?.label === c.label ? "top" : ""}`}>
                    <span>{c.label}</span><span className="pct">{Math.round(c.likelihood * 100)}%</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ) : <div className="caption">Causes are laid out once the equipment is identified.</div>}
        <div className="caption">Recommends an expert below {Math.round(sv.policy.confidence * 100)}% after {sv.policy.max_turns} rounds of checks (the condition check is one). Escalating is your call, with Escalate To Expert.</div>
      </div>

      {sv.rca && (
        <div className="card" style={{ gap: 10 }}>
          <div className="row"><Icon name="head-question-outline" size={18} color="var(--t60)" /><div className="card-title grow">5-Why</div>
            <span className="caption">{sv.rca.root ? "complete" : `${sv.rca.chain?.length || 0} answered`}</span></div>
          <WhyChain direct={sv.rca.direct_cause} chain={sv.rca.chain} root={sv.rca.root} category={sv.rca.root ? sv.rca.category : null} />
          {(sv.rca.prevent || []).length > 0 && <div className="caption">{sv.rca.prevent.length} preventive action{sv.rca.prevent.length > 1 ? "s" : ""} agreed</div>}
        </div>
      )}

      <div className="card">
        <div className="card-title">Process Topology</div>
        <div className="topo">
          {sv.topology.upstream.map((u) => <span key={u.node} className="topo-node">{u.label}</span>)}
          {sv.topology.upstream.length > 0 && <Icon name="arrow-right" className="topo-arrow" />}
          <span className="topo-node" style={{ borderColor: "var(--gps-primary)", fontWeight: 600 }}>{sv.topology.label}</span>
          {sv.topology.downstream.length > 0 && <Icon name="arrow-right" className="topo-arrow" />}
          {sv.topology.downstream.map((d) => <span key={d.node} className="topo-node">{d.label}</span>)}
        </div>
      </div>

      <div className="card">
        <div className="row"><div className="card-title grow">Similar Past Cases</div><span className="caption">similarity</span></div>
        {sv.cases.map((k) => (
          <div key={k.id} className={`case-card ${k.cited ? "cited" : ""}`}>
            <div className="row">
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--gps-primary)" }}>{k.id}</span>
              {k.cited && <span className="tag" style={{ color: "#006400", background: "#e3f2d4" }}>Referenced</span>}
              <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 600 }}>{k.sim}%</span>
            </div>
            <div style={{ color: "var(--t80)", lineHeight: 1.4 }}>{k.title}</div>
            <div className="caption" style={{ color: "var(--t60)", lineHeight: 1.4 }}>Resolution · {k.fix}</div>
          </div>
        ))}
        {!sv.cases.length && <div className="caption">{sv.equipment ? "No similar cases for this equipment type yet." : "Shown once the equipment is identified."}</div>}
      </div>

      {sv.documents.length > 0 && (
        <div className="card">
          <div className="card-title">Manual & SOP References</div>
          {sv.documents.map((d) => (
            <details key={d.doc_id + d.excerpt.slice(0, 10)}>
              <summary style={{ cursor: "pointer", color: "var(--t80)" }}><Icon name="file-document-outline" color="var(--t60)" /> {d.title}</summary>
              <div className="caption" style={{ whiteSpace: "pre-wrap", color: "var(--t70)", paddingTop: 6 }}>{d.excerpt}</div>
            </details>
          ))}
        </div>
      )}
    </section>
  );
}

function EscalateModal({ busy, onClose, onSubmit }) {
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState([]);
  const add = (list) => setFiles((cur) => [...cur, ...Array.from(list)].slice(0, MAX_FILES));
  const tooBig = files.filter((f) => f.size > MAX_FILE_BYTES);
  return (
    <Modal title="Escalate to a technical expert" onClose={onClose} width={600}>
      <div className="caption">
        The expert gets the issue report, the whole chat, the checks you've done and any files you shared. Add anything else that
        helps them analyse it — what you see, hear or smell, what you've tried, and photos or videos.
      </div>
      <div className="overline">Description for the expert</div>
      <textarea className="textarea" rows={4} value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. Knocking from the 2nd-stage valve since 10:00, gets worse under load; I topped up the oil but no change" />
      <div className="overline">Attachments · optional</div>
      {files.map((f, i) => (
        <div key={`${f.name}-${i}`} className="file-row">
          <Icon name="paperclip" color="var(--t60)" />
          <span className="grow" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
          <span className="caption" style={f.size > MAX_FILE_BYTES ? { color: "var(--gps-error)" } : undefined}>{fmtSize(f.size)}</span>
          <button className="btn ghost sm" aria-label={`Remove ${f.name}`} onClick={() => setFiles((cur) => cur.filter((_, j) => j !== i))}>
            <Icon name="close" />
          </button>
        </div>
      ))}
      {files.length < MAX_FILES && (
        <label className="btn ghost sm" style={{ alignSelf: "flex-start", cursor: "pointer" }}>
          <Icon name="paperclip" />Add Photos, Videos Or Files
          <input type="file" multiple hidden accept={FILE_TYPES}
                 onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
        </label>
      )}
      <div className="caption" style={tooBig.length ? { color: "var(--gps-error)" } : undefined}>
        {tooBig.length ? `${tooBig.map((f) => f.name).join(", ")} is over 10 MB.` : `Up to ${MAX_FILES} files, 10 MB each.`}
      </div>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn danger" disabled={busy || tooBig.length > 0} onClick={() => onSubmit({ description: description.trim(), files })}>
          {busy ? "Escalating…" : "Escalate To Expert"}
        </button>
      </div>
    </Modal>
  );
}

// The field operator confirms before the issue is closed: closing ends the chat for good
function CloseModal({ busy, identified, withExpert, reply, onClose, onConfirm }) {
  const [note, setNote] = useState("");
  const askNote = !identified && !reply;
  return (
    <Modal title="Mark this issue resolved and close it?" onClose={onClose} width={520}>
      <div className="close-summary">
        <Icon name={identified ? "check-decagram-outline" : "archive-check-outline"} size={22}
              color={identified ? "var(--gps-primary)" : "var(--t60)"} />
        <div style={{ lineHeight: 1.5 }}>
          {identified
            ? `The root cause and fix${withExpert ? " from the expert" : ""} are saved to the knowledge base, so the next person gets there faster.`
            : "No root cause has been confirmed yet, so the issue is logged to case history as closed."}
        </div>
      </div>
      <div className="caption">The chat ends and can't be reopened. If the problem comes back, report a new issue.</div>
      {askNote && (
        <>
          <div className="overline">How was it settled? · optional</div>
          <textarea className="textarea" rows={3} value={note} onChange={(e) => setNote(e.target.value)}
                    placeholder="e.g. False alarm — sensor cable was loose, re-terminated and readings are normal" />
        </>
      )}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose} disabled={busy}>Keep Troubleshooting</button>
        <button className="btn" disabled={busy} onClick={() => onConfirm(note.trim())}>
          <Icon name="check-circle-outline" />{busy ? "Closing…" : "Yes, Resolve & Close"}
        </button>
      </div>
    </Modal>
  );
}

function ResolutionModal({ busy, onClose, onSubmit }) {
  const [cause, setCause] = useState("");
  const [steps, setSteps] = useState("");
  const [note, setNote] = useState("");
  const lines = steps.split("\n").map((x) => x.trim()).filter(Boolean);
  return (
    <Modal title="Share resolution with the field operator" onClose={onClose} width={600}>
      <div className="caption">The field operator applies the steps and marks the issue resolved once it works. The RCA is saved to the knowledge base.</div>
      <input className="input" placeholder="Confirmed root cause" value={cause} onChange={(e) => setCause(e.target.value)} />
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

function OverrideModal({ interlock, onClose, onSubmit }) {
  const [reason, setReason] = useState("");
  return (
    <Modal title={`Request bypass override · ${interlock.rule_id}`} onClose={onClose} width={520}>
      <div className="safety critical"><Icon name="shield-lock-outline" /><div>{interlock.action}</div></div>
      <div className="caption">
        Overrides go to the control room for approval. Personnel-safety interlocks and bypasses without an active secondary guard
        filter are blocked automatically.
      </div>
      <textarea className="textarea" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is the override needed?" />
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn danger" disabled={!reason.trim()} onClick={() => onSubmit(reason)}>Submit Request</button>
      </div>
    </Modal>
  );
}
