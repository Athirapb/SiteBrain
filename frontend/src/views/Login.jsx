import { useEffect, useState } from "react";
import { api, setToken } from "../api";
import { Icon } from "../components/ui";

const ROLE_INFO = {
  field_operator: ["hard-hat", "Field Operator", "Report issues, guided troubleshooting, safety sign-offs"],
  expert: ["account-tie-outline", "Technical Expert", "Escalations, control room approvals, dashboards, plant setup, knowledge"],
};

export default function Login({ onDone }) {
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.get("/api/auth/users", { site: false }).then(setUsers).catch((e) => setErr(e.message));
  }, []);

  const signIn = async (username) => {
    try {
      const r = await api.post("/api/auth/login", { username }, { site: false });
      setToken(r.token);
      onDone();
    } catch (e) {
      setErr(e.message);
    }
  };

  return (
    <div className="login">
      <div className="login-card">
        <div className="brand">
          <div className="brand-mark" style={{ width: 40, height: 40, flexBasis: 40 }}><Icon name="hexagon-multiple" size={24} /></div>
          <div>
            <div className="brand-name" style={{ fontSize: 20 }}>SiteBrain AI</div>
            <div className="brand-sub">BUU OPERATIONS COPILOT</div>
          </div>
        </div>
        <div className="page-sub">
          Sign in as one of the demo users. Each role sees its own workspace (SRS §2 role-based access).
        </div>
        {err && <div className="safety critical"><Icon name="alert-circle-outline" />{err} — is the backend running on port 8000?</div>}
        <div className="role-grid">
          {users.map((u) => {
            const [icon, label, desc] = ROLE_INFO[u.role] || ["account", u.role, ""];
            return (
              <button key={u.username} className="role-card" onClick={() => signIn(u.username)}>
                <Icon name={icon} />
                <div style={{ fontWeight: 600, fontSize: 15 }}>{u.name}</div>
                <div style={{ fontSize: 13, color: "var(--gps-primary)", fontWeight: 600 }}>{label}</div>
                <div className="caption">{u.title}{u.site_code ? ` · ${u.site_code}` : " · all sites"}</div>
                <div className="caption" style={{ color: "var(--t60)" }}>{desc}</div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
