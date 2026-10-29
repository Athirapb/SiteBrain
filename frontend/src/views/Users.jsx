import { useMemo, useState } from "react";
import { api } from "../api";
import { Empty, Icon, Modal, PillTabs, Spinner, fmtDate, useAsync } from "../components/ui";

const ROLE_TABS = [["all", "All"], ["field_operator", "Field Operators"], ["expert", "Experts"]];

// The administrator adds the people who report issues and the experts who answer them
export default function Users({ notify }) {
  const users = useAsync(() => api.get("/api/admin/users", { site: false }), []);
  const opts = useAsync(() => api.get("/api/admin/options", { site: false }), []);
  const [tab, setTab] = useState("all");
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(null); // null | {} (new) | user
  const [pwFor, setPwFor] = useState(null); // the user getting a new password

  const siteName = (code) => opts.data?.sites.find((s) => s.code === code)?.name || code;
  const listed = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (users.data || []).filter((u) => u.role !== "admin" && (tab === "all" || u.role === tab))
      .filter((u) => !q || [u.name, u.email, u.title].join(" ").toLowerCase().includes(q));
  }, [users.data, tab, query]);

  const toggleActive = async (u) => {
    try {
      await api.put(`/api/admin/users/${u.id}`, { active: !u.active }, { site: false });
      notify(u.active ? `${u.name} can no longer sign in` : `${u.name} can sign in again`);
      users.reload();
    } catch (e) { notify(e.message, true); }
  };
  const remove = async (u) => {
    if (!window.confirm(`Delete ${u.name}? This can't be undone.`)) return;
    try {
      await api.del(`/api/admin/users/${u.id}`, { site: false });
      notify(`${u.name} deleted`);
      users.reload();
    } catch (e) { notify(e.message, true); }
  };

  return (
    <div className="page narrow">
      <div className="row wrap" style={{ alignItems: "flex-end" }}>
        <div className="grow">
          <div className="page-title">Users</div>
          <div className="page-sub">Add the people who report issues and the experts who answer them, with the password they sign in with.</div>
        </div>
        <button className="btn lg" onClick={() => setEditing({})} disabled={!opts.data}><Icon name="account-plus-outline" />Add User</button>
      </div>
      <div className="row wrap" style={{ gap: 12 }}>
        <PillTabs value={tab} onChange={setTab} options={ROLE_TABS} />
        <div className="search grow" style={{ minWidth: 200 }}>
          <Icon name="magnify" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a user" aria-label="Find a user" />
        </div>
      </div>
      {!users.data ? <Spinner /> : (
        <div className="hist-list">
          {listed.map((u) => (
            <div key={u.id} className="card user-row" style={{ opacity: u.active ? 1 : 0.6 }}>
              <div className="profile-avatar">{u.name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase()}</div>
              <div className="grow" style={{ minWidth: 0 }}>
                <div className="row wrap" style={{ gap: 8 }}>
                  <b style={{ color: "var(--t90)" }}>{u.name}</b>
                  <span className="tag" style={{ background: u.role === "expert" ? "var(--gps-info-lgt)" : "var(--gps-primary-lgt)",
                                                 color: u.role === "expert" ? "#1c6fc1" : "var(--gps-green-dark)" }}>{u.role_label}</span>
                  {!u.active && <span className="tag" style={{ background: "var(--page)", color: "var(--t60)" }}>Switched off</span>}
                  {u.active && !u.has_password && <span className="tag" style={{ background: "var(--gps-orange-lgt)", color: "var(--gps-orange-dark)" }}>No password</span>}
                </div>
                <div className="caption ellipsis">{u.email}{u.title ? ` · ${u.title}` : ""}</div>
                <div className="caption">{u.site_code ? siteName(u.site_code) : "All plants"}{u.area_code ? ` · ${u.area_code}` : ""} · added {fmtDate(u.created_at)}</div>
              </div>
              <div className="row wrap" style={{ gap: 6 }}>
                <button className="btn ghost sm" onClick={() => setEditing(u)}><Icon name="pencil-outline" />Edit</button>
                <button className="btn ghost sm" onClick={() => setPwFor(u)}><Icon name="lock-reset" />Set Password</button>
                <button className="btn ghost sm" onClick={() => toggleActive(u)}>{u.active ? "Switch Off" : "Switch On"}</button>
                <button className="btn ghost sm" onClick={() => remove(u)} aria-label={`Delete ${u.name}`} title="Delete"><Icon name="trash-can-outline" /></button>
              </div>
            </div>
          ))}
          {!listed.length && (
            <div className="card"><Empty icon="account-group-outline" title={query ? "Nobody matches" : "No users yet"}>
              {!query && "Add the field operators and experts so they can sign in."}
            </Empty></div>
          )}
        </div>
      )}
      {editing && opts.data && (
        <UserModal user={editing} opts={opts.data} notify={notify} onClose={() => setEditing(null)}
                   onSaved={() => { setEditing(null); users.reload(); }} />
      )}
      {pwFor && <PasswordModal user={pwFor} notify={notify} onClose={() => setPwFor(null)} onSaved={() => { setPwFor(null); users.reload(); }} />}
    </div>
  );
}

function UserModal({ user, opts, notify, onClose, onSaved }) {
  const isNew = !user.id;
  const [f, setF] = useState({
    name: user.name || "", email: user.email || "", role: user.role || "field_operator", title: user.title || "",
    site_code: user.site_code || "", project_id: user.project_id || "", area_code: user.area_code || "", password: "",
  });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF((cur) => ({ ...cur, [k]: e.target.value, ...(k === "site_code" ? { area_code: "" } : {}) }));
  const role = opts.roles.find((r) => r.id === f.role);
  const areas = opts.areas.filter((a) => a.site_code === f.site_code);
  const needsSite = f.role === "field_operator";
  const ok = f.name.trim() && (!isNew || (f.email.trim() && f.password.length >= 8)) && (!needsSite || f.site_code);

  const save = async () => {
    setBusy(true);
    const body = { name: f.name.trim(), role: f.role, title: f.title.trim() || null, site_code: f.site_code || null,
                   project_id: f.project_id ? Number(f.project_id) : null, area_code: f.area_code || null };
    try {
      const r = isNew
        ? await api.post("/api/admin/users", { ...body, email: f.email.trim(), password: f.password }, { site: false })
        : await api.put(`/api/admin/users/${user.id}`, body, { site: false });
      notify(isNew ? `${body.name} added. Give them their email and password.` : "Saved");
      onSaved(r);
    } catch (e) { notify(e.message, true); } finally { setBusy(false); }
  };

  return (
    <Modal title={isNew ? "Add a user" : `Edit ${user.name}`} onClose={onClose} width={560}>
      <div className="field"><span className="overline">Role</span>
        <PillTabs value={f.role} onChange={(v) => setF((c) => ({ ...c, role: v, title: "" }))} options={opts.roles.map((r) => [r.id, r.label])} />
      </div>
      <label className="field"><span className="overline">Name</span>
        <input className="input" value={f.name} onChange={set("name")} placeholder="Full name" /></label>
      <label className="field"><span className="overline">Email · used to sign in</span>
        <input className="input" type="email" value={f.email} onChange={set("email")} disabled={!isNew} placeholder="name@gpsrenewables.com" /></label>
      <label className="field"><span className="overline">Designation</span>
        <input className="input" list="titles" value={f.title} onChange={set("title")} placeholder={role?.titles[0]} />
        <datalist id="titles">{role?.titles.map((t) => <option key={t} value={t} />)}</datalist></label>
      <label className="field"><span className="overline">Plant{needsSite ? "" : " · leave empty for all plants"}</span>
        <select className="select" value={f.site_code} onChange={set("site_code")}>
          <option value="">{needsSite ? "Select the plant…" : "All plants"}</option>
          {opts.sites.map((s) => <option key={s.code} value={s.code}>{s.name} ({s.code})</option>)}
        </select></label>
      {f.site_code && (
        <label className="field"><span className="overline">Usual area · filled in on their issue reports</span>
          <select className="select" value={f.area_code} onChange={set("area_code")}>
            <option value="">No usual area</option>
            {areas.map((a) => <option key={a.code} value={a.code}>{a.name} ({a.code})</option>)}
          </select></label>
      )}
      <label className="field"><span className="overline">Usual project · filled in on their issue reports</span>
        <select className="select" value={f.project_id} onChange={set("project_id")}>
          <option value="">No usual project</option>
          {opts.projects.map((p) => <option key={p.id} value={p.id}>{p.name}{p.name !== p.code ? ` (${p.code})` : ""}</option>)}
        </select></label>
      {isNew && <PasswordField value={f.password} onChange={(v) => setF((c) => ({ ...c, password: v }))} />}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn" disabled={busy || !ok} onClick={save}>{isNew ? "Add User" : "Save"}</button>
      </div>
    </Modal>
  );
}

// A password the administrator types or generates, shown so it can be passed on to the user
function PasswordField({ value, onChange }) {
  const generate = () => {
    const abc = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    const bytes = crypto.getRandomValues(new Uint8Array(10));
    onChange(Array.from(bytes, (b) => abc[b % abc.length]).join(""));
  };
  return (
    <label className="field"><span className="overline">Password · at least 8 characters</span>
      <div className="row">
        <input className="input grow" type="text" autoComplete="new-password" value={value}
               onChange={(e) => onChange(e.target.value)} placeholder="Type one, or generate it" />
        <button type="button" className="btn ghost sm" onClick={generate}><Icon name="dice-multiple-outline" />Generate</button>
        <button type="button" className="btn ghost sm" disabled={!value}
                onClick={() => navigator.clipboard?.writeText(value)}><Icon name="content-copy" />Copy</button>
      </div>
      <span className="caption">Give it to the user yourself. It is not shown again after you save.</span>
    </label>
  );
}

function PasswordModal({ user, notify, onClose, onSaved }) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/api/admin/users/${user.id}/password`, { password }, { site: false });
      notify(`New password set for ${user.name}. They have been signed out.`);
      onSaved();
    } catch (e) { notify(e.message, true); } finally { setBusy(false); }
  };
  return (
    <Modal title={`Set a new password for ${user.name}`} onClose={onClose} width={520}>
      <div className="caption">{user.email} · they are signed out and use the new password from now on.</div>
      <PasswordField value={password} onChange={setPassword} />
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn" disabled={busy || password.length < 8} onClick={save}>Set Password</button>
      </div>
    </Modal>
  );
}
