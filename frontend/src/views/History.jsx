import { useMemo, useState } from "react";
import { api } from "../api";
import { Empty, Icon, Modal, PillTabs, Spinner, URGENCY_BG, fmtDate, fmtDuration, fmtTime, useAsync } from "../components/ui";

// status filter → which cases it keeps, and how a case's outcome reads
const STATUS_TABS = [["All", "All"], ["open", "Open"], ["SiteBrain", "Resolved By SiteBrain"], ["Expert", "Resolved By Expert"], ["closed", "Closed"]];
const KEEP = {
  All: () => true,
  open: (h) => h.status === "active" || h.status === "escalated",
  SiteBrain: (h) => h.status === "resolved" && h.resolved_by === "SiteBrain",
  Expert: (h) => h.status === "resolved" && h.resolved_by === "Expert",
  closed: (h) => h.status === "closed",
};
const outcome = (h) =>
  h.status === "active" ? ["In progress", "var(--gps-orange)", "progress-wrench"]
    : h.status === "escalated" ? ["With expert", "var(--gps-info)", "account-hard-hat-outline"]
    : h.status === "closed" ? ["Closed", "var(--t50)", "archive-check-outline"]
    : h.resolved_by === "Expert" ? ["Resolved by expert", "var(--gps-info)", "check-decagram-outline"]
    : ["Resolved by SiteBrain", "var(--gps-green-mid)", "check-decagram-outline"];
const NO_EQ = "__area__"; // equipment filter value for issues whose equipment was never identified

export default function History({ user, nav }) {
  const data = useAsync(() => api.get("/api/sessions?limit=1000"), []);
  const [project, setProject] = useState("All");
  const [eq, setEq] = useState("All");
  const [status, setStatus] = useState("All");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(null);
  const rows = data.data || [];

  // filter options come from the cases themselves, with counts, so no option leads to an empty list
  const projects = useMemo(() => {
    const m = new Map();
    rows.forEach((h) => {
      const k = h.project_id ? String(h.project_id) : "";
      if (!k) return;
      const cur = m.get(k) || { id: k, name: h.project, code: h.project_code, n: 0 };
      cur.n += 1;
      m.set(k, cur);
    });
    return [...m.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [rows]);
  const inProject = useMemo(() => rows.filter((h) => project === "All" || String(h.project_id) === project), [rows, project]);
  const equipmentByArea = useMemo(() => {
    const areas = new Map();
    inProject.forEach((h) => {
      const area = areas.get(h.unit_name) || new Map();
      const k = h.area_level ? NO_EQ : h.equipment_id;
      const cur = area.get(k) || { id: k, name: h.area_level ? "Equipment not identified" : h.eq_name, n: 0 };
      cur.n += 1;
      area.set(k, cur);
      areas.set(h.unit_name, area);
    });
    return [...areas.entries()].sort(([a], [b]) => a.localeCompare(b))
      .map(([area, m]) => [area, [...m.values()].sort((a, b) => a.name.localeCompare(b.name))]);
  }, [inProject]);

  const byEq = useMemo(() => inProject.filter((h) => {
    if (eq === "All") return true;
    const [area, id] = eq.split("|||");
    return h.unit_name === area && (h.area_level ? NO_EQ : h.equipment_id) === id;
  }), [inProject, eq]);
  const listed = useMemo(() => {
    const q = query.trim().toLowerCase();
    return byEq.filter(KEEP[status]).filter((h) => !q || [h.id, h.symptom, h.root_cause, h.eq_name, h.unit_name, h.project,
      h.project_code, h.reported_by].join(" ").toLowerCase().includes(q));
  }, [byEq, status, query]);

  const counts = Object.fromEntries(STATUS_TABS.map(([k]) => [k, byEq.filter(KEEP[k]).length]));
  const done = listed.filter((h) => h.duration_min != null && ["resolved", "closed"].includes(h.status));
  const avg = done.length ? done.reduce((a, h) => a + h.duration_min, 0) / done.length : null;
  const filtered = project !== "All" || eq !== "All" || status !== "All" || query.trim();
  const clear = () => { setProject("All"); setEq("All"); setStatus("All"); setQuery(""); };

  return (
    <div className="page" style={{ gap: 16 }}>
      <div className="card hist-filters">
        <div className="search grow" style={{ minWidth: 220 }}>
          <Icon name="magnify" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search issue, root cause, session or person"
                 aria-label="Search case history" />
          {query && <button className="btn ghost sm" onClick={() => setQuery("")} aria-label="Clear search"><Icon name="close" /></button>}
        </div>
        <label className="hist-select">
          <Icon name="briefcase-outline" />
          <select className="select" value={project} aria-label="Project filter"
                  onChange={(e) => { setProject(e.target.value); setEq("All"); }}>
            <option value="All">All projects</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}{p.code && p.code !== p.name ? ` (${p.code})` : ""} · {p.n}</option>)}
          </select>
        </label>
        <label className="hist-select">
          <Icon name="cog-outline" />
          <select className="select" value={eq} aria-label="Equipment filter" onChange={(e) => setEq(e.target.value)}>
            <option value="All">All equipment</option>
            {equipmentByArea.map(([area, items]) => (
              <optgroup key={area} label={area}>
                {items.map((e) => <option key={e.id} value={`${area}|||${e.id}`}>{e.name} · {e.n}</option>)}
              </optgroup>
            ))}
          </select>
        </label>
        {filtered && <button className="btn ghost sm" onClick={clear}><Icon name="filter-remove-outline" />Clear Filters</button>}
      </div>

      <div className="row wrap" style={{ justifyContent: "space-between" }}>
        <PillTabs value={status} onChange={setStatus} options={STATUS_TABS.map(([k, label]) => [k, `${label} · ${counts[k]}`])} />
        {data.data && (
          <span className="caption">
            {listed.length} case{listed.length === 1 ? "" : "s"}{avg != null ? ` · average ${fmtDuration(avg)} to close` : ""}
          </span>
        )}
      </div>

      {!data.data ? <Spinner /> : (
        <div className="hist-list">
          {listed.map((h) => {
            const [label, color, icon] = outcome(h);
            return (
              <button key={h.id} className="hist-card" style={{ "--accent": color }} onClick={() => setOpen(h.id)}>
                <div className="hist-top">
                  <span className="hist-title">{h.symptom || "Reported issue"}</span>
                  <span className="tag" style={{ background: URGENCY_BG[h.severity], color: "#fff" }}>{h.severity}</span>
                  <span className="hist-status" style={{ color }}><Icon name={icon} size={16} />{label}</span>
                </div>
                <div className="hist-meta">
                  {h.project && <span className="hist-chip project"><Icon name="briefcase-outline" size={14} />{h.project}</span>}
                  <span className="hist-chip">
                    <Icon name={h.area_level ? "map-marker-question-outline" : h.icon} size={14} />
                    <b>{h.area_level ? "Equipment not identified" : h.eq_name}</b>· {h.unit_name}
                  </span>
                  <span className="hist-chip"><Icon name="calendar-outline" size={14} />{fmtDate(h.created_at)}</span>
                  {h.duration_min != null && ["resolved", "closed"].includes(h.status) && (
                    <span className="hist-chip"><Icon name="timer-outline" size={14} />{fmtDuration(h.duration_min)}</span>
                  )}
                  {h.reported_by && <span className="hist-chip"><Icon name="account-outline" size={14} />{h.reported_by}</span>}
                  <span className="hist-chip id">{h.id}</span>
                </div>
                {h.root_cause && (
                  <div className="hist-cause"><span className="overline">Root cause</span><span>{h.root_cause}</span></div>
                )}
              </button>
            );
          })}
          {!listed.length && (
            <div className="card">
              <Empty icon="file-search-outline" title={rows.length ? "No cases match these filters" : "No cases yet"}>
                {rows.length ? <button className="btn ghost sm" onClick={clear}>Clear Filters</button> : "Issues reported in the copilot show up here."}
              </Empty>
            </div>
          )}
        </div>
      )}
      {open && <SessionModal sid={open} onClose={() => setOpen(null)} canOpen={user.permissions.includes("copilot")}
                             onOpen={() => nav("copilot", { sessionId: open })} />}
    </div>
  );
}

function SessionModal({ sid, onClose, onOpen, canOpen }) {
  const d = useAsync(() => api.get(`/api/sessions/${sid}`), [sid]);
  const v = d.data;
  const s = v?.session;
  return (
    <Modal title={s ? s.symptom || "Reported issue" : `Session ${sid}`} onClose={onClose}>
      {!v ? <Spinner /> : (
        <>
          <div className="row wrap">
            <Icon name={v.icon} size={22} color="var(--gps-primary)" />
            <div className="grow" style={{ minWidth: 0 }}>
              <b>{v.equipment ? v.equipment.name : "Equipment not identified"}</b> · {v.area.name}
              <div className="caption">
                {sid}{s.report?.project ? ` · ${s.report.project}` : ""} · {s.status} · severity {s.severity} · {s.turns} checks
                {" · "}reported {fmtTime(s.created_at)}{s.report?.reported_by ? ` by ${s.report.reported_by}` : ""}
              </div>
            </div>
            {canOpen && <button className="btn sm" onClick={onOpen}>Open In Copilot</button>}
          </div>
          {s.root_cause && (
            <div className="panel solution">
              <div className="overline">Root Cause</div>
              <b>{s.root_cause}</b>
              {(s.steps || []).map((x, i) => <div key={i} className="step"><span className="step-n">{i + 1}</span>{x}</div>)}
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {v.messages.filter((m) => ["report", "user", "agent", "analysis", "event"].includes(m.type)).map((m) => (
              <div key={m.id} style={{ fontSize: 13, lineHeight: 1.5 }}>
                <b style={{ color: ["user", "report"].includes(m.type) ? "var(--gps-primary)" : m.type === "event" ? "var(--t50)" : m.expert ? "var(--gps-info)" : "var(--t80)" }}>
                  {["user", "report"].includes(m.type) ? m.author || "Field operator" : m.type === "event" ? "•" : m.who || "SiteBrain"}
                </b>{" "}
                <span style={{ color: m.type === "event" ? "var(--t60)" : undefined }}>{m.text}</span>
                {(m.attachments || []).length > 0 && (
                  <span className="caption"> <Icon name="paperclip" size={13} />{m.attachments.map((f) => f.filename).join(", ")}</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </Modal>
  );
}
