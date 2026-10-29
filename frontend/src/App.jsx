import { useCallback, useEffect, useState } from "react";
import { api, getSite, getToken, setSite, setToken } from "./api";
import { Icon, Spinner, usePoll } from "./components/ui";
import Login from "./views/Login";
import Report from "./views/Report";
import Issue from "./views/Issue";
import Issues from "./views/Issues";
import KnowledgeBase from "./views/KnowledgeBase";
import Users from "./views/Users";

// One action at a time: three sections per role, the most frequent one first
const NAV = {
  field_operator: [
    { id: "report", label: "Report An Issue", icon: "clipboard-alert-outline" },
    { id: "issues", label: "My Past Issues", icon: "history" },
    { id: "kb", label: "Knowledge Base", icon: "book-open-variant" },
  ],
  expert: [
    { id: "queue", label: "Issues Queue", icon: "inbox-arrow-down-outline" },
    { id: "resolutions", label: "My Past Resolutions", icon: "check-decagram-outline" },
    { id: "kb", label: "Knowledge Base", icon: "book-open-variant" },
  ],
  admin: [{ id: "users", label: "Users", icon: "account-multiple-outline" }],
};
const ROUTES = new Set(["report", "issues", "kb", "queue", "resolutions", "users", "issue"]);

export default function App() {
  const [meta, setMeta] = useState(null);
  const [authed, setAuthed] = useState(!!getToken());
  const [view, setView] = useState(null);
  const [params, setParams] = useState({});
  const [equipment, setEquipment] = useState([]);
  const [badge, setBadge] = useState(0);
  const [toast, setToast] = useState(null);

  const notify = useCallback((text, error = false) => {
    setToast({ text, error });
    setTimeout(() => setToast(null), 3800);
  }, []);

  const endSession = useCallback(() => {
    setToken(null);
    setAuthed(false);
    setMeta(null);
    setView(null);
    window.location.hash = "";
  }, []);
  const signOut = useCallback(async () => {
    try { await api.post("/api/auth/logout", {}, { site: false }); } catch { /* already signed out */ }
    endSession();
  }, [endSession]);

  const nav = useCallback((v, p = {}) => {
    setParams(p);
    setView(v);
    window.location.hash = v === "issue" && p.sessionId ? `issue/${p.sessionId}` : v;
  }, []);

  useEffect(() => {
    if (!authed) return;
    api.get("/api/meta", { site: false })
      .then((m) => {
        const codes = m.sites.map((s) => s.code);
        if (!getSite() || !codes.includes(getSite())) setSite(m.user.site_code || codes[0]);
        setMeta(m);
        const home = NAV[m.user.role]?.[0]?.id || "kb";
        const [hv, sid] = window.location.hash.replace("#", "").split("/");
        const allowed = ROUTES.has(hv) && (hv === "issue" ? !!sid && m.user.role !== "admin"
          : (NAV[m.user.role] || []).some((n) => n.id === hv));
        if (allowed) { setView(hv); setParams(hv === "issue" ? { sessionId: sid } : {}); } else setView(home);
      })
      .catch((e) => (e.status === 401 ? endSession() : notify(e.message, true)));
  }, [authed, endSession, notify]);

  // reporter: issues with an unread expert reply; expert: escalations waiting on an expert
  const refreshShared = useCallback(() => {
    if (!meta) return;
    const role = meta.user.role;
    if (role === "field_operator") {
      api.get("/api/equipment").then(setEquipment).catch(() => {});
      api.get("/api/sessions?mine=true&status=open&limit=200")
        .then((r) => setBadge(r.filter((x) => x.expert_replied).length)).catch(() => {});
    } else if (role === "expert") {
      api.get("/api/escalations?scope=fleet&status=open&limit=200")
        .then((r) => setBadge(r.items.filter((x) => !x.claimed_by || x.awaiting_expert).length)).catch(() => {});
    }
  }, [meta]);

  useEffect(refreshShared, [refreshShared]);
  usePoll(refreshShared, 15000, [refreshShared]);

  if (!authed) return <Login onDone={() => setAuthed(true)} />;
  if (!meta || !view) return <Spinner text="Connecting to SiteBrain…" />;

  const user = meta.user;
  const items = NAV[user.role] || [];
  const home = items[0]?.id;
  const site = meta.sites.find((s) => s.code === getSite()) || meta.sites[0];
  const active = view === "issue" ? (params.from || (user.role === "expert" ? "queue" : "issues")) : view;
  const ctx = { meta, user, site, equipment, refreshShared, nav, notify, params };
  const badgeFor = (id) => (id === "issues" || id === "queue" ? badge : 0);

  return (
    <div className="app">
      <aside className="sidebar">
        <button className="brand brand-btn" onClick={() => nav(home)} title="Home" aria-label="SiteBrain home">
          <div className="brand-mark"><Icon name="hexagon-multiple" size={18} /></div>
          <div>
            <div className="brand-name">SiteBrain</div>
            <div className="brand-sub">PLANT COPILOT</div>
          </div>
        </button>
        <nav className="nav">
          {items.map((v) => (
            <button key={v.id} className={`nav-btn ${active === v.id ? "active" : ""}`} onClick={() => nav(v.id)}>
              <Icon name={v.icon} />
              <span className="nav-text">{v.label}</span>
              {badgeFor(v.id) > 0 && <span className="badge">{badgeFor(v.id)}</span>}
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <div className="profile">
            <div className="profile-avatar">{(user.name || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase()}</div>
            <div className="grow" style={{ minWidth: 0 }}>
              <div className="profile-name ellipsis" title={user.name}>{user.name}</div>
              <div className="caption ellipsis">{user.title || user.role_label}</div>
            </div>
          </div>
          <button className="btn outline-danger signout" onClick={signOut}><Icon name="logout" />Sign Out</button>
        </div>
      </aside>

      <main className="main" key={view === "issue" ? `issue-${params.sessionId}` : view}>
        {view === "report" && <Report {...ctx} />}
        {view === "issue" && <Issue {...ctx} />}
        {view === "issues" && <Issues {...ctx} mode="mine" />}
        {view === "queue" && <Issues {...ctx} mode="queue" />}
        {view === "resolutions" && <Issues {...ctx} mode="resolved" />}
        {view === "kb" && <KnowledgeBase {...ctx} />}
        {view === "users" && <Users {...ctx} />}
      </main>
      {toast && <div className={`toast ${toast.error ? "error" : ""}`} role="status">{toast.text}</div>}
    </div>
  );
}
