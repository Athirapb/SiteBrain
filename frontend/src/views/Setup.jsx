import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Empty, Icon, Modal, Spinner, useAsync } from "../components/ui";

export default function Setup({ meta, nav, notify, refreshShared }) {
  const areas = useAsync(() => api.get("/api/areas?include_inactive=true"), []);
  const eqs = useAsync(() => api.get("/api/equipment?include_inactive=true"), []);
  const [areaId, setAreaId] = useState(null);
  const [query, setQuery] = useState("");
  const [editArea, setEditArea] = useState(null); // {} = new area
  const [editEq, setEditEq] = useState(null); // {} = new equipment

  useEffect(() => {
    if (areas.data?.length && !areas.data.some((a) => a.id === areaId)) setAreaId(areas.data[0].id);
  }, [areas.data, areaId]);

  const area = areas.data?.find((a) => a.id === areaId);
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (eqs.data || []).filter((e) => e.area_id === areaId)
      .filter((e) => !q || `${e.name} ${e.kind} ${e.tag || ""}`.toLowerCase().includes(q));
  }, [eqs.data, areaId, query]);

  const reload = () => {
    areas.reload();
    eqs.reload();
    refreshShared();
  };

  const run = async (fn, ok) => {
    try {
      const r = await fn();
      notify(ok);
      reload();
      return r || true;
    } catch (e) {
      notify(e.message, true);
      return null;
    }
  };

  const saveArea = async (f) => {
    const body = { code: f.code, name: f.name, description: f.description || "", active: f.active };
    const r = await run(() => (f.id ? api.put(`/api/areas/${f.id}`, body) : api.post("/api/areas", body)),
                        f.id ? `${f.name} updated` : `${f.name} added`);
    if (r) {
      setEditArea(null);
      if (!f.id && r.id) setAreaId(r.id);
    }
  };
  const deleteArea = (a) => {
    if (window.confirm(`Delete the area ${a.name}? This cannot be undone.`))
      run(() => api.del(`/api/areas/${a.id}`), `${a.name} deleted`).then((r) => r && setAreaId(null));
  };
  const saveEq = async (f) => {
    const body = { area_id: Number(f.area_id), name: f.name, kind: f.kind, tag: f.tag || null, active: f.active };
    const r = await run(() => (f.id ? api.put(`/api/equipment?id=${encodeURIComponent(f.id)}`, body) : api.post("/api/equipment", body)),
                        f.id ? `${f.name} updated` : `${f.name} added`);
    if (r) setEditEq(null);
  };
  const toggleEq = (e) => run(() => api.put(`/api/equipment?id=${encodeURIComponent(e.id)}`,
                                            { area_id: e.area_id, name: e.name, kind: e.kind, tag: e.tag, active: !e.active }),
                              `${e.name} ${e.active ? "deactivated" : "activated"}`);
  const deleteEq = (e) => {
    if (window.confirm(`Delete ${e.name}? This cannot be undone.`)) run(() => api.del(`/api/equipment?id=${encodeURIComponent(e.id)}`), `${e.name} deleted`);
  };

  const COLS = "minmax(180px,2fr) 130px minmax(110px,1fr) 110px 150px";
  return (
    <div className="page" style={{ flexDirection: "row", flexWrap: "wrap", alignItems: "flex-start" }}>
      <section style={{ flex: "0 1 300px", minWidth: 240, display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="row">
          <div className="section-title grow">Areas</div>
          <button className="btn sm" onClick={() => setEditArea({ active: true })}><Icon name="plus" />Add Area</button>
        </div>
        <div className="eq-list" style={{ maxHeight: "calc(100vh - 230px)" }}>
          {!areas.data ? <Spinner /> : areas.data.map((a) => (
            <button key={a.id} className={`eq-item ${a.id === areaId ? "sel" : ""}`} onClick={() => setAreaId(a.id)}
                    style={a.active ? undefined : { opacity: 0.6 }}>
              <Icon name="map-marker-outline" color={a.id === areaId ? "var(--gps-primary)" : undefined} />
              <div className="grow" style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span className="eq-name">{a.name}</span>
                <span className="caption">{a.code} · {a.equipment_count} equipment{a.open_issues ? ` · ${a.open_issues} open issue${a.open_issues > 1 ? "s" : ""}` : ""}</span>
              </div>
              {!a.active && <span className="tag" style={{ background: "var(--t10)", color: "var(--t60)" }}>Inactive</span>}
            </button>
          ))}
          {areas.data && !areas.data.length && <Empty icon="map-marker-plus-outline" title="No areas yet">Add the first area of this plant.</Empty>}
        </div>
      </section>

      <section style={{ flex: "1 1 560px", minWidth: 0, display: "flex", flexDirection: "column", gap: 16 }}>
        {!area ? (areas.data ? <Empty icon="sitemap-outline" title="Select an area" /> : <Spinner />) : (
          <>
            <div className="card" style={{ flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
              <Icon name="map-marker-outline" size={32} color="var(--gps-primary)" />
              <div className="grow" style={{ minWidth: 200 }}>
                <div className="section-title">{area.name} {!area.active && <span className="tag" style={{ background: "var(--t10)", color: "var(--t60)" }}>Inactive</span>}</div>
                <div className="caption">{area.code}{area.description ? ` · ${area.description}` : ""}</div>
              </div>
              <button className="btn ghost sm" onClick={() => nav("copilot", { report: { areaId: area.id } })} disabled={!area.active}>
                <Icon name="clipboard-alert-outline" />Report Issue
              </button>
              <button className="btn ghost sm" onClick={() => setEditArea(area)}><Icon name="pencil-outline" />Edit</button>
              <button className="btn ghost sm" onClick={() => deleteArea(area)} disabled={area.equipment_total > 0}
                      title={area.equipment_total ? "Move or delete its equipment first" : "Delete this area"}><Icon name="delete-outline" />Delete</button>
            </div>

            <div className="row wrap">
              <div className="search" style={{ flex: "1 1 240px", maxWidth: 360 }}>
                <Icon name="magnify" />
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find equipment" aria-label="Find equipment" />
              </div>
              <span className="caption grow">{rows.length} equipment</span>
              <button className="btn" onClick={() => setEditEq({ area_id: area.id, kind: meta.kinds[0], active: true })}>
                <Icon name="plus" />Add Equipment
              </button>
            </div>

            <div className="table">
              <div style={{ minWidth: 700 }}>
                <div className="trow head" style={{ gridTemplateColumns: COLS }}>
                  <span>Equipment</span><span>Type</span><span>Tag</span><span>Status</span><span />
                </div>
                {!eqs.data ? <Spinner /> : rows.map((e) => (
                  <div key={e.id} className="trow" style={{ gridTemplateColumns: COLS, opacity: e.active ? 1 : 0.6 }}>
                    <span className="row" style={{ gap: 8 }}><Icon name={e.icon} color="var(--t60)" /><span style={{ color: "var(--t80)", fontWeight: 500 }}>{e.name}</span></span>
                    <span className="muted">{e.kind}</span>
                    <span className="caption">{e.tag || "—"}</span>
                    <span>
                      <button className="opt" onClick={() => toggleEq(e)} title={e.active ? "Click to deactivate" : "Click to activate"}
                              style={e.active ? { color: "var(--gps-green-dark)", borderColor: "var(--gps-primary)" } : undefined}>
                        {e.active ? "Active" : "Inactive"}
                      </button>
                    </span>
                    <span className="row" style={{ justifyContent: "flex-end", gap: 4 }}>
                      <button className="btn ghost sm" onClick={() => setEditEq(e)} aria-label={`Edit ${e.name}`}><Icon name="pencil-outline" /></button>
                      <button className="btn ghost sm" onClick={() => deleteEq(e)} aria-label={`Delete ${e.name}`}><Icon name="delete-outline" /></button>
                    </span>
                  </div>
                ))}
                {eqs.data && !rows.length && <div style={{ padding: "24px 16px", color: "var(--t50)" }}>No equipment in this area yet.</div>}
              </div>
            </div>
            <div className="caption">
              Inactive areas and equipment are hidden from issue reporting but keep their history. Anything with issue history can only be deactivated, not deleted.
            </div>
          </>
        )}
      </section>

      {editArea && <AreaModal area={editArea} onClose={() => setEditArea(null)} onSave={saveArea} />}
      {editEq && <EquipmentModal eq={editEq} areas={areas.data || []} kinds={meta.kinds} onClose={() => setEditEq(null)} onSave={saveEq} />}
    </div>
  );
}

function Field({ label, children }) {
  return <label style={{ display: "flex", flexDirection: "column", gap: 6 }}><span className="overline">{label}</span>{children}</label>;
}

function AreaModal({ area, onClose, onSave }) {
  const [f, setF] = useState({ code: "", name: "", description: "", active: true, ...area });
  return (
    <Modal title={area.id ? `Edit area · ${area.name}` : "Add area"} onClose={onClose} width={520}>
      <Field label="Code"><input className="input" value={f.code} maxLength={12} placeholder="e.g. D5" onChange={(e) => setF({ ...f, code: e.target.value.toUpperCase() })} /></Field>
      <Field label="Name"><input className="input" value={f.name} placeholder="e.g. Digester 5" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
      <Field label="Description"><textarea className="textarea" rows={2} value={f.description || ""} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
      <label className="check-row"><input type="checkbox" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} /><span>Active — issues can be reported in this area</span></label>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn" disabled={!f.code.trim() || !f.name.trim()} onClick={() => onSave(f)}>Save Area</button>
      </div>
    </Modal>
  );
}

function EquipmentModal({ eq, areas, kinds, onClose, onSave }) {
  const [f, setF] = useState({ name: "", tag: "", ...eq });
  return (
    <Modal title={eq.id ? `Edit equipment · ${eq.name}` : "Add equipment"} onClose={onClose} width={520}>
      <Field label="Name"><input className="input" value={f.name} placeholder="e.g. D5 Agitator 1" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
      <Field label="Type">
        <select className="select" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
          {kinds.map((k) => <option key={k}>{k}</option>)}
        </select>
      </Field>
      <div className="caption">The type decides which field checks and causes SiteBrain uses when troubleshooting.</div>
      <Field label="Area">
        <select className="select" value={f.area_id} onChange={(e) => setF({ ...f, area_id: Number(e.target.value) })}>
          {areas.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.code})</option>)}
        </select>
      </Field>
      <Field label="Tag · optional"><input className="input" value={f.tag || ""} placeholder="e.g. P-101" onChange={(e) => setF({ ...f, tag: e.target.value })} /></Field>
      <label className="check-row"><input type="checkbox" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} /><span>Active — available when reporting issues</span></label>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn" disabled={!f.name.trim()} onClick={() => onSave(f)}>Save Equipment</button>
      </div>
    </Modal>
  );
}
