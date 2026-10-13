import { useState } from "react";
import { api } from "../api";
import { Empty, Icon, Modal, PillTabs, Spinner, STATUS_COLOR, fmtTime, useAsync, usePoll } from "../components/ui";

const LANES = [
  ["Gas train", ["DIG", "SCR", "FLT", "BLW", "LPC", "CHL", "MEM", "HPC", "CBG"]],
  ["Off-spec", ["MEM", "FLR"]],
  ["Slurry", ["FEED", "DIG", "SLS", "CDT"]],
  ["Utilities", ["HWG", "DIG"], ["CW", "CHL"]],
];

export default function ControlRoom({ user, nav, notify, refreshShared }) {
  const [filter, setFilter] = useState("active");
  const [release, setRelease] = useState(null);
  const canAct = user.permissions.includes("control");
  const topo = useAsync(() => api.get("/api/topology"), []);
  const il = useAsync(() => api.get(`/api/control/interlocks?status=${filter}`), [filter]);
  const ov = useAsync(() => api.get("/api/control/overrides"), []);
  const audit = useAsync(() => api.get("/api/audit?limit=60"), []);
  usePoll(() => { il.reload(); ov.reload(); audit.reload(); topo.reload(); }, 8000, [filter]);

  const decide = async (o, approve) => {
    const note = approve ? "Approved with guard filter verified active" : "Rejected — fix the cause first";
    try {
      await api.post(`/api/control/overrides/${o.id}/decide`, { approve, note });
      notify(approve ? "Override approved; interlock released" : "Override rejected");
      ov.reload(); il.reload(); audit.reload(); refreshShared();
    } catch (e) { notify(e.message, true); }
  };

  const doRelease = async (note) => {
    try {
      await api.post(`/api/control/interlocks/${release.id}/release`, { note });
      notify(`${release.rule_id} released`);
      setRelease(null); il.reload(); audit.reload(); refreshShared();
    } catch (e) { notify(e.message, true); }
  };

  const nodes = Object.fromEntries((topo.data?.nodes || []).map((n) => [n.id, n]));
  const pending = (ov.data || []).filter((o) => o.status === "pending");

  return (
    <div className="page">
      <div className="card">
        <div className="row"><div className="card-title grow">Process Map · Asset Topology</div>
          <span className="legend">{["Normal", "Abnormal", "Critical"].map((s) => <span key={s}><i style={{ background: STATUS_COLOR[s] }} />{s}</span>)}</span></div>
        {!topo.data ? <Spinner /> : LANES.map(([lane, ...chains]) => (
          <div key={lane} className="row wrap" style={{ gap: 10 }}>
            <span className="overline" style={{ width: 80 }}>{lane}</span>
            {chains.map((chain, ci) => (
              <div key={ci} className="topo">
                {chain.map((id, i) => (
                  <span key={id + i} className="row" style={{ gap: 6 }}>
                    {i > 0 && <Icon name="arrow-right" className="topo-arrow" />}
                    <span className="topo-node" style={{ borderColor: STATUS_COLOR[nodes[id]?.status] || "var(--t10)", borderWidth: nodes[id]?.status !== "Normal" ? 2 : 1 }}>
                      <span className="dot" style={{ background: STATUS_COLOR[nodes[id]?.status] }} />{nodes[id]?.label}
                    </span>
                  </span>
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ alignItems: "start" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, gridColumn: "1 / -1" }}>
          <div className="row wrap">
            <div className="section-title grow">Interlock & Bypass Status Tracker</div>
            {il.data && (
              <span className="chip">
                <Icon name="air-filter" size={16} color={il.data.guard_filter_active ? "var(--gps-green-mid)" : "var(--gps-error)"} />
                Secondary guard filter {il.data.guard_filter_active ? "ACTIVE" : "INACTIVE"}
              </span>
            )}
            <PillTabs value={filter} onChange={setFilter} options={[["active", "Active"], ["24h", "Last 24 h"], ["all", "All"]]} />
          </div>
          <div className="table">
            <div style={{ minWidth: 900 }}>
              <div className="trow head" style={{ gridTemplateColumns: "90px minmax(160px,1fr) minmax(240px,2fr) 160px 100px 140px" }}>
                <span>Rule</span><span>Equipment</span><span>Action</span><span>Status</span><span>Raised</span><span></span>
              </div>
              {!il.data ? <Spinner /> : il.data.items.map((i) => (
                <div key={i.id} className="trow" style={{ gridTemplateColumns: "90px minmax(160px,1fr) minmax(240px,2fr) 160px 100px 140px" }}>
                  <span style={{ fontWeight: 600, color: i.category === "interlock" ? "var(--gps-red)" : "var(--gps-orange-dark)" }}>
                    <Icon name={i.category === "interlock" ? "shield-lock-outline" : "shield-alert-outline"} /> {i.rule_id}
                  </span>
                  <span>{i.eq_name}<div className="caption">{i.unit_name}</div></span>
                  <span style={{ lineHeight: 1.4 }}>{i.action}<div className="caption">{i.reason}</div></span>
                  <span className="status-text" style={{ fontSize: 12, color: i.status === "engaged" ? "var(--gps-red)" : i.status === "released" ? "var(--gps-green-mid)" : "var(--gps-orange-dark)" }}>
                    {i.status === "engaged" ? "Awaiting sign-off" : i.status}
                  </span>
                  <span className="caption">{i.age}</span>
                  <span className="row" style={{ justifyContent: "flex-end" }}>
                    {i.session_id && <button className="btn ghost sm" title="Open session" onClick={() => nav("copilot", { sessionId: i.session_id })}><Icon name="message-text-outline" /></button>}
                    {canAct && i.status !== "released" && (
                      <button className="btn outline sm" disabled={i.status === "engaged"} title={i.status === "engaged" ? "Field sign-off pending" : "Release after verification"}
                              onClick={() => setRelease(i)}>Release</button>
                    )}
                  </span>
                </div>
              ))}
              {il.data && !il.data.items.length && <div style={{ padding: 16, color: "var(--t50)" }}>No interlocks in this view.</div>}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="row"><div className="card-title grow">Manual Override Approval Gate</div>
            {pending.length > 0 && <span className="badge">{pending.length} pending</span>}</div>
          {!ov.data ? <Spinner /> : ov.data.slice(0, 12).map((o) => (
            <div key={o.id} style={{ borderBottom: "1px solid var(--t10)", paddingBottom: 10, display: "flex", flexDirection: "column", gap: 4 }}>
              <div className="row wrap">
                <b>{o.rule_id}</b><span className="muted">{o.eq_name}</span>
                <span className="status-text" style={{ marginLeft: "auto", fontSize: 12,
                  color: { pending: "var(--gps-orange-dark)", approved: "var(--gps-green-mid)", rejected: "var(--t60)", blocked: "var(--gps-red)" }[o.status] }}>{o.status}</span>
              </div>
              <div className="caption" style={{ color: "var(--t70)" }}>“{o.reason}” — {o.requested_by} · {fmtTime(o.created_at)}</div>
              {o.decision_note && <div className="caption">{o.decided_by}: {o.decision_note}</div>}
              {o.status === "pending" && canAct && (
                <div className="row">
                  <button className="btn success sm" onClick={() => decide(o, true)}>Approve</button>
                  <button className="btn ghost sm" onClick={() => decide(o, false)}>Reject</button>
                </div>
              )}
            </div>
          ))}
          {ov.data && !ov.data.length && <Empty icon="lock-check-outline" title="No override requests" />}
        </div>

        <div className="card">
          <div className="row"><div className="card-title grow">Audit Trail</div><span className="caption">append-only</span></div>
          <div style={{ maxHeight: 420, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
            {(audit.data || []).map((a) => (
              <div key={a.id} style={{ fontSize: 13, borderBottom: "1px solid var(--t10)", paddingBottom: 6 }}>
                <div className="row"><b className="grow">{a.action}</b><span className="caption">{fmtTime(a.ts)}</span></div>
                <div className="caption" style={{ color: "var(--t70)" }}>{a.actor} ({a.role}){a.entity ? ` · ${a.entity}` : ""}
                  {a.detail && Object.keys(a.detail).length ? ` · ${Object.entries(a.detail).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" · ")}` : ""}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      {release && <ReleaseModal il={release} onClose={() => setRelease(null)} onSubmit={doRelease} />}
    </div>
  );
}

function ReleaseModal({ il, onClose, onSubmit }) {
  const [note, setNote] = useState("");
  return (
    <Modal title={`Release ${il.rule_id} · ${il.eq_name}`} onClose={onClose} width={520}>
      <div className="safety critical"><Icon name="shield-lock-outline" /><div>{il.action}</div></div>
      <div className="caption">Record how the cause was verified fixed. This entry is written to the immutable audit trail.</div>
      <textarea className="textarea" rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Oil topped up to 70%, leak fixed, verified at 14:20" />
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn" disabled={!note.trim()} onClick={() => onSubmit(note)}>Release Interlock</button>
      </div>
    </Modal>
  );
}
