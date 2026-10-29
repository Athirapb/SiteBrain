import { useState } from "react";
import { api, setToken } from "../api";
import { Icon } from "../components/ui";

// The sign-in cards (like the GPS LLF app): pick the account type, then sign in with email and password
const ACCOUNTS = {
  field_operator: { icon: "hard-hat", title: "Field Operator", sub: "Shift In-Charge, Engineers, Plant Manager" },
  expert: { icon: "account-tie-outline", title: "Technical Expert", sub: "Central O&M team, Design Engineers" },
  admin: { icon: "shield-account-outline", title: "Administrator", sub: "Manage users" },
};

export default function Login({ onDone }) {
  const [type, setType] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const pick = (t) => { setType(t); setErr(null); setPassword(""); };
  const signIn = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await api.post("/api/auth/login", { email: email.trim(), password, account_type: type }, { site: false });
      setToken(r.token);
      onDone();
    } catch (x) {
      setErr(x.status ? x.message : "Can't reach SiteBrain. Is the server running?");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <aside className="login-brand">
        <div className="brand">
          <div className="brand-mark lg"><Icon name="hexagon-multiple" size={26} /></div>
          <div>
            <div className="brand-name" style={{ fontSize: 22, color: "#fff" }}>SiteBrain</div>
            <div className="brand-sub" style={{ color: "#e3f2d4" }}>PLANT TROUBLESHOOTING COPILOT</div>
          </div>
        </div>
        <div className="login-pitch">
          <div className="login-headline">Your plant troubleshooting copilot</div>
          <div className="login-feats">
            {[["message-text-outline", "Simple chat", "Feels like messaging a colleague"],
              ["book-open-variant", "Plant knowledge built in", "SOPs, past cases, your plant"],
              ["shoe-print", "Step-by-step guidance", "One check at a time"],
              ["account-group-outline", "Expert help when needed", "With the full story attached"]].map(([icon, t, s]) => (
              <div key={t} className="login-feat">
                <span className="login-feat-icon"><Icon name={icon} size={20} /></span>
                <div><div style={{ fontWeight: 600 }}>{t}</div><div style={{ fontSize: 13, opacity: 0.85 }}>{s}</div></div>
              </div>
            ))}
          </div>
        </div>
        <div className="caption" style={{ color: "#e3f2d4" }}>© GPS Renewables</div>
      </aside>

      <main className="login-main">
        <div className="login-card">
          {!type ? (
            <>
              <div>
                <div className="login-title">Sign in</div>
                <div className="page-sub">Choose your account type to continue.</div>
              </div>
              {["field_operator", "expert"].map((t) => (
                <button key={t} className="account-card" onClick={() => pick(t)}>
                  <span className="account-icon"><Icon name={ACCOUNTS[t].icon} size={24} /></span>
                  <span className="grow">
                    <span className="account-title">{ACCOUNTS[t].title}</span>
                    <span className="caption">{ACCOUNTS[t].sub}</span>
                  </span>
                  <span className="btn sm">Sign in <Icon name="arrow-right" /></span>
                </button>
              ))}
              <div className="caption">
                Forgot your password? Contact your administrator. ·{" "}
                <button className="link-btn" onClick={() => pick("admin")}>Administrator sign in</button>
              </div>
            </>
          ) : (
            <form onSubmit={signIn} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <button type="button" className="link-btn" style={{ alignSelf: "flex-start" }} onClick={() => pick(null)}>
                <Icon name="arrow-left" /> All account types
              </button>
              <div className="row" style={{ gap: 12 }}>
                <span className="account-icon"><Icon name={ACCOUNTS[type].icon} size={24} /></span>
                <div>
                  <div className="login-title" style={{ fontSize: 22 }}>{ACCOUNTS[type].title}</div>
                  <div className="caption">{ACCOUNTS[type].sub}</div>
                </div>
              </div>
              <label className="field">
                <span className="overline">Email</span>
                <input className="input lg" type="email" autoComplete="username" required autoFocus value={email}
                       onChange={(e) => setEmail(e.target.value)} placeholder="name@gpsrenewables.com" />
              </label>
              <label className="field">
                <span className="overline">Password</span>
                <input className="input lg" type="password" autoComplete="current-password" required value={password}
                       onChange={(e) => setPassword(e.target.value)} />
              </label>
              {err && <div className="safety critical"><Icon name="alert-circle-outline" /><div>{err}</div></div>}
              <button className="btn lg" disabled={busy || !email.trim() || !password}>
                {busy ? "Signing in…" : "Sign in"} <Icon name="arrow-right" />
              </button>
              <div className="caption">Forgot your password? Contact your administrator.</div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
