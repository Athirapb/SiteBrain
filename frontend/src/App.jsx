import { useCallback, useEffect, useMemo, useState } from "react";
import { api, getSite, getToken, setSite, setToken } from "./api";
import { Icon, Spinner, usePoll } from "./components/ui";
import Login from "./views/Login";
import Copilot from "./views/Copilot";
import KnowledgeBase from "./views/KnowledgeBase";
import Escalations from "./views/Escalations";
import History from "./views/History";
import ControlRoom from "./views/ControlRoom";
import Dashboards from "./views/Dashboards";
import Setup from "./views/Setup";

const VIEWS = [
  { id: "copilot", label: "Copilot", icon: "message-processing-outline", perm: "copilot",
    title: "Operations Copilot", sub: "Report an issue on an area or equipment, troubleshoot it step by step, apply a proven resolution" },
  { id: "esc", label: "Escalations", icon: "account-group-outline", perm: "esc.read",
    title: "Escalations", sub: "Sessions handed to technical experts with full diagnostic context" },
  { id: "control", label: "Control Room", icon: "shield-lock-outline", perm: "control.read",
    title: "Control Room", sub: "Safety interlocks, bypass override approvals and the immutable audit trail" },
  { id: "dash", label: "Dashboards", icon: "chart-box-outline", perm: "dash",
    title: "Operational Dashboards", sub: "Daily stability, weekly reliability and monthly executive summaries" },
  { id: "kb", label: "Knowledge Base", icon: "book-open-variant", perm: "kb.read",
    title: "Knowledge Base", sub: "The knowledge brain: RCA cases, fishbone & 5-Why troubleshooting library, operating conditions and manuals" },
  { id: "hist", label: "Case History", icon: "history", perm: "history",
    title: "Case History", sub: "Every diagnostic session, how it was resolved and how long it took" },
  { id: "setup", label: "Plant Setup", icon: "sitemap-outline", perm: "config",
    title: "Plant Setup", sub: "Configure the areas of this plant and the equipment in each area" },
];

const ROLE_HOME = { field_operator: "copilot", expert: "esc" };

export default function App() {
  const [meta, setMeta] = useState(null);
  const [authed, setAuthed] = useState(!!getToken());
  const [view, setView] = useState(null);
  const [params, setParams] = useState({});
  const [equipment, setEquipment] = useState([]);
  const [openEsc, setOpenEsc] = useState(0);
  const [openIssues, setOpenIssues] = useState([]);
  const [toast, setToast] = useState(null);
  const [siteKey, setSiteKey] = useState(0);

  const notify = useCallback((text, error = false) => {
    setToast({ text, error });
    setTimeout(() => setToast(null), 3800);
  }, []);

  const signOut = useCallback(() => {
    setToken(null);
    setAuthed(false);
    setMeta(null);
    setView(null);
  }, []);

  useEffect(() => {
    if (!authed) return;
    api.get("/api/meta", { site: false })
      .then((m) => {
        const codes = m.sites.map((s) => s.code);
        if (!getSite() || !codes.includes(getSite())) setSite(m.user.site_code || codes[0]);
        setMeta(m);
        const allowed = VIEWS.filter((v) => m.user.permissions.includes(v.perm)).map((v) => v.id);
        const fromHash = window.location.hash.replace("#", "");
        setView(allowed.includes(fromHash) ? fromHash : ROLE_HOME[m.user.role] || allowed[0]);
      })
      .catch((e) => (e.status === 401 ? signOut() : notify(e.message, true)));
  }, [authed, signOut, notify]);

  const refreshShared = useCallback(() => {
    if (!meta) return;
    api.get("/api/equipment").then(setEquipment).catch(() => {});
    if (meta.user.permissions.includes("history"))
      api.get("/api/sessions?status=open&limit=200").then(setOpenIssues).catch(() => {});
    if (meta.user.permissions.includes("esc.read"))
      api.get("/api/escalations?status=open&limit=1").then((r) => setOpenEsc(r.stats.open)).catch(() => {});
  }, [meta]);

  useEffect(refreshShared, [refreshShared, siteKey]);
  usePoll(refreshShared, 15000, [refreshShared]);

  const nav = useCallback((v, p = {}) => {
    setParams(p);
    setView(v);
    window.location.hash = v;
  }, []);

  const views = useMemo(() => (meta ? VIEWS.filter((v) => meta.user.permissions.includes(v.perm)) : []), [meta]);

  if (!authed) return <Login onDone={() => setAuthed(true)} />;
  if (!meta || !view) return <Spinner text="Connecting to SiteBrain…" />;

  const cur = VIEWS.find((v) => v.id === view);
  const site = meta.sites.find((s) => s.code === getSite()) || meta.sites[0];
  const units = new Set(equipment.map((e) => e.unit)).size;
  const ctx = { meta, user: meta.user, site, equipment, openIssues, refreshShared, nav, notify, params };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Icon name="hexagon-multiple" size={18} /></div>
          <div>
            <div className="brand-name">SiteBrain</div>
            <div className="brand-sub">PLANT COPILOT</div>
          </div>
        </div>
        <nav className="nav">
          <div className="nav-label">Workspace</div>
          {views.map((v) => (
            <button key={v.id} className={`nav-btn ${view === v.id ? "active" : ""}`} onClick={() => nav(v.id)}>
              <Icon name={v.icon} />
              <span style={{ flex: "1 1 auto" }}>{v.id === "esc" && meta.user.role === "expert" ? "Expert Queue" : v.label}</span>
              {v.id === "esc" && openEsc > 0 && <span className="badge">{openEsc}</span>}
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <div className="caption" style={{ textTransform: "uppercase" }}>Plant</div>
          {meta.sites.length > 1 ? (
            <select className="select" value={site.code} aria-label="Site"
                    onChange={(e) => { setSite(e.target.value); setSiteKey((k) => k + 1); setParams({}); }}>
              {meta.sites.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
            </select>
          ) : null}
          <div className="site-box">
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--t80)" }}>{site.name}</div>
            <div className="caption">{site.code} · {units} areas · {equipment.length} equipment</div>
          </div>
          <div className="site-box row">
            <Icon name="account-circle-outline" size={22} color="var(--t60)" />
            <div className="grow">
              <div style={{ fontSize: 13, fontWeight: 600 }}>{meta.user.name}</div>
              <div className="caption">{meta.user.title}</div>
            </div>
            <button className="btn ghost sm" onClick={signOut} title="Sign out" aria-label="Sign out"><Icon name="logout" /></button>
          </div>
        </div>
      </aside>

      <main className="main" key={`${site.code}-${siteKey}`}>
        <header className="header">
          <div style={{ flex: "1 1 260px", minWidth: 0 }}>
            <div className="page-title">{cur.title}</div>
            <div className="page-sub">{cur.sub}</div>
          </div>
          <div className="row wrap">
            <div className="chip"><span className="dot live" />Shift {meta.current_shift.shift} in progress · {meta.current_shift.date}</div>
            {meta.user.permissions.includes("copilot") && (
              <button className="chip" style={{ cursor: "pointer" }} onClick={() => nav("copilot")}>
                <Icon name="alert-outline" size={16} color="var(--gps-error)" />
                {openIssues.length} open issue{openIssues.length === 1 ? "" : "s"}
              </button>
            )}
            <div className="chip" title={meta.llm.reason || ""}>
              <Icon name={meta.llm.enabled ? "creation" : "file-tree-outline"} size={16} color="var(--gps-primary)" />
              {meta.llm.enabled ? `${meta.llm.label} · ${meta.llm.model}` : "Decision-tree engine"}
            </div>
          </div>
        </header>
        {view === "copilot" && <Copilot {...ctx} />}
        {view === "kb" && <KnowledgeBase {...ctx} />}
        {view === "esc" && <Escalations {...ctx} />}
        {view === "hist" && <History {...ctx} />}
        {view === "control" && <ControlRoom {...ctx} />}
        {view === "dash" && <Dashboards {...ctx} />}
        {view === "setup" && <Setup {...ctx} />}
      </main>
      {toast && <div className={`toast ${toast.error ? "error" : ""}`} role="status">{toast.text}</div>}
    </div>
  );
}
