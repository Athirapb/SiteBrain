import { useState } from "react";
import { api } from "../api";
import { Attachment, Empty, Icon, Modal, PillTabs, Spinner, Stat, URGENCY_BG, fmtTime, useAsync, usePoll } from "../components/ui";
import { Sparkline } from "../components/charts";

const STATUS_COLOR = { Resolved: "#28a745", Active: "#3191ef", "In Progress": "#ffa500" };

export default function Escalations({ user, equipment, nav, notify }) {
  const [eqFilter, setEqFilter] = useState("All");
  const [status, setStatus] = useState("all");
  const [open, setOpen] = useState(null);
  const [respond, setRespond] = useState(null);
  const q = `/api/escalations?${eqFilter !== "All" ? `equipment_id=${encodeURIComponent(eqFilter)}&` : ""}${status === "open" ? "status=open" : ""}`;
  const data = useAsync(() => api.get(q), [q]);
  usePoll(() => data.reload(), 8000, [q]);
  const canWork = user.permissions.includes("esc.work");

  const units = [...new Set(equipment.map((e) => e.unit_name))];
  const st = data.data?.stats;

  const claim = async (t) => {
    try {
      await api.post(`/api/escalations/${t}/claim`);
      notify(`You now own ${t}. Open the chat to talk with the field operator.`);
      data.reload();
    } catch (e) { notify(e.message, true); }
  };

  return (
    <div className="page">
      <div className="stats">
        <Stat label="Open" value={st?.open} />
        <Stat label="Escalation Rate · 30 d" value={st?.rate_30d_pct} unit="%" />
        <Stat label="Mean Expert Response" value={st?.mean_response_min} unit="min" />
        <Stat label="Resolved By Experts · 30 d" value={st?.resolved_by_experts_30d} />
        <Stat label="Context Package Compile" value={st?.mean_compile_ms} unit="ms" hint="SRS target < 30 s" />
      </div>
      <div className="row wrap">
        <Icon name="filter-variant" size={20} color="var(--t60)" />
        <select className="select pill" value={eqFilter} onChange={(e) => setEqFilter(e.target.value)} aria-label="Equipment filter">
          <option value="All">All Equipment</option>
          {units.map((u) => (
            <optgroup key={u} label={u}>
              {equipment.filter((e) => e.unit_name === u).map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
            </optgroup>
          ))}
        </select>
        <PillTabs value={status} onChange={setStatus} options={[["all", "All"], ["open", "Open Only"]]} />
        {data.data && <span className="caption">{data.data.items.length} escalations</span>}
      </div>
      {!data.data ? <Spinner /> : data.data.items.map((e) => {
        const mine = e.claimed_by === user.id;
        return (
          <div key={e.ticket} className="card" style={{ boxShadow: "none", border: `1px solid ${e.status !== "Resolved" ? "var(--gps-primary)" : "var(--t10)"}`, flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: 16 }}>
            <div style={{ flex: "1 1 320px", minWidth: 0, display: "flex", flexDirection: "column", gap: 4 }}>
              <div className="row wrap" style={{ gap: 10 }}>
                <span style={{ fontWeight: 600, color: "var(--gps-primary)" }}>{e.ticket}</span>
                <span className="tag" style={{ background: URGENCY_BG[e.urgency], color: "#fff" }}>{e.urgency}</span>
                <span className="caption" style={{ color: "var(--t60)" }}>{e.unit_name} · {e.area_level ? "equipment not identified" : e.eq_name}</span>
              </div>
              <div style={{ lineHeight: 1.5, color: "var(--t80)" }}>{e.summary}</div>
              <div className="caption"><Icon name="flash-outline" /> {e.trigger_reason}</div>
              <div className="caption">
                {e.claimed_by ? e.expert_name : "Awaiting an expert"} · {e.expert_role}{mine ? " (you)" : e.claimed_by ? "" : e.status !== "Resolved" ? " · unclaimed" : ""} · {e.turns} AI checks before escalation · raised {e.age}
              </div>
            </div>
            <span className="status-text" style={{ fontSize: 12, color: STATUS_COLOR[e.status] }}>{e.status}</span>
            <div className="row wrap">
              <button className="btn ghost sm" onClick={() => setOpen(e.ticket)}><Icon name="code-json" />Payload</button>
              {e.session_id && <button className="btn sm" onClick={() => nav("copilot", { sessionId: e.session_id })}>Open Chat</button>}
              {canWork && e.status !== "Resolved" && !mine && <button className="btn outline sm" onClick={() => claim(e.ticket)}>Claim</button>}
              {canWork && e.status !== "Resolved" && e.session_id && (
                <button className="btn outline sm" onClick={() => setRespond(e)}>Respond</button>
              )}
            </div>
          </div>
        );
      })}
      {data.data && !data.data.items.length && <Empty icon="account-check-outline" title="No escalations">The copilot resolved everything here.</Empty>}
      {open && <PayloadModal ticket={open} onClose={() => setOpen(null)} />}
      {respond && <RespondModal esc={respond} onClose={() => setRespond(null)} notify={notify} onDone={() => { setRespond(null); data.reload(); }} />}
    </div>
  );
}

function PayloadModal({ ticket, onClose }) {
  const d = useAsync(() => api.get(`/api/escalations/${ticket}`), [ticket]);
  const [tab, setTab] = useState("request");
  const p = d.data?.payload;
  return (
    <Modal title={`Escalation context package · ${ticket}`} onClose={onClose} width={900}>
      {!d.data ? <Spinner /> : !p?.escalation_metadata ? (
        <div className="caption">This is an archived escalation; its context package was not retained in the demo seed.</div>
      ) : (
        <>
          <div className="caption">Compiled and dispatched in {d.data.compile_ms} ms · {fmtTime(d.data.created_at)}</div>
          <PillTabs value={tab} onChange={setTab} options={[["request", `Operator's Request${d.data.attachments.length ? ` · ${d.data.attachments.length} files` : ""}`], ["summary", "Diagnostic Matrix"], ["scada", "30-min SCADA"], ["transcript", "Transcript"], ["digest", "Email / SMS Digest"], ["json", "JSON Payload"]]} />
          {tab === "request" && (
            <div className="card" style={{ boxShadow: "none", border: "1px solid var(--t10)" }}>
              <div className="caption">Escalated by {p.operator_request?.requested_by || "the field operator"}</div>
              <div style={{ lineHeight: 1.5, whiteSpace: "pre-wrap" }}>{p.operator_request?.description || <span className="caption">No description given.</span>}</div>
              {d.data.attachments.length > 0 && (
                <div className="row wrap" style={{ gap: 8 }}>
                  {d.data.attachments.map((f) => <Attachment key={f.id} ticket={ticket} file={f} />)}
                </div>
              )}
            </div>
          )}
          {tab === "summary" && (
            <div className="table">
              <div className="trow head" style={{ gridTemplateColumns: "120px minmax(180px,2fr) 120px 110px 90px" }}>
                <span>Checkpoint</span><span>Description</span><span>Input</span><span>Expected</span><span>Status</span>
              </div>
              {p.diagnostic_summary.checkpoint_matrix.map((c) => (
                <div key={c.checkpoint_id} className="trow" style={{ gridTemplateColumns: "120px minmax(180px,2fr) 120px 110px 90px" }}>
                  <span className="caption">{c.checkpoint_id}</span><span>{c.description}</span><span>{c.operator_input}</span>
                  <span className="caption">{c.expected}</span>
                  <span className="status-text" style={{ color: c.status === "FAILED" ? "var(--gps-red)" : c.status === "PASSED" ? "var(--gps-green-mid)" : "var(--t60)" }}>{c.source === "issue report" && c.status === "FAILED" ? "REPORTED" : c.status}</span>
                </div>
              ))}
            </div>
          )}
          {tab === "scada" && (
            <div className="card" style={{ boxShadow: "none", border: "1px solid var(--t10)" }}>
              {!Object.keys(p.telemetry_window_30min).length && <div className="caption">No SCADA window: the equipment was not identified when this was escalated.</div>}
              {Object.entries(p.telemetry_window_30min).map(([k, v]) => (
                <div key={k} className="spark">
                  <span className="grow" style={{ color: "var(--t80)" }}>{k}</span>
                  {Array.isArray(v) && <Sparkline values={v} width={200} />}
                  <span style={{ minWidth: 220, textAlign: "right", fontFamily: "monospace", fontSize: 12 }}>{Array.isArray(v) ? v.join(", ") : v}</span>
                </div>
              ))}
            </div>
          )}
          {tab === "transcript" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {p.conversation_transcript.map((t, i) => (
                <div key={i}><b style={{ color: ["field operator", "technician"].includes(t.role) ? "var(--gps-primary)" : "var(--gps-info)" }}>{t.role}:</b> {t.text}</div>
              ))}
            </div>
          )}
          {tab === "digest" && d.data.outbox.map((o, i) => (
            <div key={i} className="card" style={{ boxShadow: "none", border: "1px solid var(--t10)" }}>
              <div className="row"><b className="grow">{o.channel.toUpperCase()} → {o.recipient}</b><span className="caption">{o.status}</span></div>
              <pre className="code" style={{ whiteSpace: "pre-wrap" }}>{o.body}</pre>
            </div>
          ))}
          {tab === "json" && <pre className="code">{JSON.stringify(p, null, 2)}</pre>}
        </>
      )}
    </Modal>
  );
}

function RespondModal({ esc, onClose, notify, onDone }) {
  const [text, setText] = useState("");
  const [cause, setCause] = useState("");
  const [steps, setSteps] = useState("");
  const send = async () => {
    try {
      await api.post(`/api/sessions/${esc.session_id}/expert-message`, {
        text, root_cause: cause || null, steps: cause ? steps.split("\n").map((s) => s.trim()).filter(Boolean) : null,
      });
      notify("Sent to the field operator");
      onDone();
    } catch (e) { notify(e.message, true); }
  };
  return (
    <Modal title={`Respond on ${esc.ticket}`} onClose={onClose} width={600}>
      <div className="caption">Responding claims the ticket for you. You can also reply from the chat itself (Open Chat).</div>
      <textarea className="textarea" rows={3} placeholder="Message to the field operator" value={text} onChange={(e) => setText(e.target.value)} />
      <div className="overline">Resolution (optional)</div>
      <input className="input" placeholder="Confirmed root cause" value={cause} onChange={(e) => setCause(e.target.value)} />
      <textarea className="textarea" rows={4} placeholder="Resolution steps, one per line" value={steps} onChange={(e) => setSteps(e.target.value)} disabled={!cause} />
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn" onClick={send} disabled={!text.trim() && !(cause.trim() && steps.trim())}>Send</button>
      </div>
    </Modal>
  );
}
