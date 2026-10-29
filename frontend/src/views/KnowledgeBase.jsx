import { useEffect, useState } from "react";
import { api } from "../api";
import { Empty, Icon, Modal, PillTabs, Spinner, fmtDate, useAsync, usePoll } from "../components/ui";
import History from "./History";
import { CAT_COLOR, CAT_LABEL, CatChip, Fishbone, WhyChain } from "../components/rca";

const KINDS = ["Agitator", "Pump", "Compressor", "Blower", "Decanter", "WAM", "Shredder", "HWG", "Chiller", "Scrubber", "Filter", "Membrane", "Machine"];

export default function KnowledgeBase({ user, notify, nav }) {
  const [tab, setTab] = useState("cases");
  const canWrite = user.permissions.includes("kb.write");
  const stats = useAsync(() => api.get("/api/kb/brain"), []);
  const [training, setTraining] = useState(false);
  const train = async () => {
    setTraining(true);
    try {
      const r = await api.post("/api/kb/train");
      notify(`Knowledge base updated · ${r.documents_added} new and ${r.documents_updated} updated documents`);
      stats.reload();
    } catch (e) { notify(e.message, true); } finally { setTraining(false); }
  };
  const hist = stats.data?.history_import;
  usePoll(() => stats.reload(), hist?.running ? 4000 : 0, [hist?.running]);
  // reporters see what helps on the floor; experts also see how SiteBrain reasons and the operating envelopes
  const tabs = [["cases", "Past Cases"], ["hist", "Case History"], ["docs", "Manuals & SOPs"],
                ...(canWrite ? [["lib", "Troubleshooting Library"], ["cond", "Operating Conditions"]] : [])];
  return (
    <div className="page">
      <div>
        <div className="page-title">Knowledge Base</div>
        <div className="page-sub">How past problems were solved, every issue reported in the plant, and the manuals and SOPs.</div>
      </div>
      <div className="row wrap">
        <PillTabs value={tab} onChange={setTab} options={tabs} />
        <span className="grow" />
        {canWrite && <button className="btn ghost sm" onClick={train} disabled={training}><Icon name="refresh" />{training ? "Updating…" : "Refresh Knowledge"}</button>}
      </div>
      {hist?.running && (
        <div className="safety" style={{ alignItems: "center" }}>
          <Icon name="loading" className="spin" />
          <div className="grow">Reading historic PIR / RCA reports into the knowledge base · {hist.done} of {hist.total} files</div>
        </div>
      )}
      {tab === "cases" && <Cases canWrite={canWrite} notify={notify} />}
      {tab === "hist" && <History user={user} nav={nav} embedded />}
      {tab === "lib" && <Library />}
      {tab === "cond" && <Conditions />}
      {tab === "docs" && <Docs canWrite={canWrite} notify={notify} />}
    </div>
  );
}

function Library() {
  const lib = useAsync(() => api.get("/api/kb/troubleshooting"), []);
  const [kind, setKind] = useState(null);
  const cur = lib.data?.find((e) => e.kind === kind) || lib.data?.[0];
  if (!lib.data) return <Spinner />;
  return (
    <>
      <div className="caption">How SiteBrain troubleshoots each equipment type: a fishbone of direct causes narrowed by field checks, then a 5-Why down to the root cause.</div>
      <PillTabs value={cur?.kind} onChange={setKind} options={lib.data.map((e) => [e.kind, `${e.kind} (${e.count})`])} />
      {cur && (
        <>
          <div className="card">
            <div className="row"><Icon name={cur.icon} size={22} color="var(--gps-primary)" /><div className="section-title grow">{cur.kind} · fishbone</div>
              <span className="caption">{cur.causes.length} direct causes · {cur.checks.length} field checks</span></div>
            <Fishbone problem={`${cur.kind} failure`} showPct={false} max={6}
                      bones={Object.values(cur.causes.reduce((acc, c) => {
                        (acc[c.category] ||= { category: c.category, label: c.category_label, causes: [] }).causes.push({ label: c.label });
                        return acc;
                      }, {}))} />
          </div>
          <div className="grid-2">
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="section-title">Direct causes & their 5-Why</div>
              {cur.causes.map((c) => (
                <details key={c.label} className="card" style={{ gap: 8 }}>
                  <summary className="row" style={{ cursor: "pointer" }}><span className="grow" style={{ fontWeight: 600, color: "var(--t80)" }}>{c.label}</span><CatChip category={c.category} /></summary>
                  <div className="overline" style={{ paddingTop: 8 }}>Immediate corrective actions</div>
                  {c.steps.map((x, i) => <div key={i} className="caption" style={{ color: "var(--t70)" }}>{i + 1}. {x}</div>)}
                  {c.why && <><div className="overline" style={{ paddingTop: 8 }}>5-Why tree</div><WhyTree node={c.why} /></>}
                </details>
              ))}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="section-title">Field checks</div>
              {cur.checks.map((q) => (
                <div key={q.text} className="card" style={{ gap: 4 }}>
                  <div style={{ color: "var(--t80)", lineHeight: 1.4, fontWeight: 500 }}>{q.text}</div>
                  <div className="caption">{q.options.join(" · ")}</div>
                  {q.purpose && <div className="purpose"><Icon name="lightbulb-on-outline" size={14} /><span>{q.purpose}</span></div>}
                  {q.how && <div className="caption" style={{ color: "var(--t60)" }}><b>How:</b> {q.how}</div>}
                </div>
              ))}
              <Learning kind={cur.kind} />
              {cur.maintenance && <Maintenance m={cur.maintenance} />}
            </div>
          </div>
        </>
      )}
    </>
  );
}

function Learning({ kind }) {
  const d = useAsync(() => api.get(`/api/kb/learning?kind=${encodeURIComponent(kind)}`), [kind]);
  const k = d.data?.kinds?.[0];
  if (!k) return null;
  const max = Math.max(...k.causes.map((c) => Math.max(c.authored_share, c.learned_share)));
  return (
    <div className="card" style={{ gap: 8 }}>
      <div className="row"><Icon name="school-outline" size={18} color="var(--t60)" /><div className="card-title grow">Learned from resolved sessions</div>
        <span className="caption">{k.sessions} session{k.sessions === 1 ? "" : "s"}</span></div>
      {!k.sessions ? (
        <div className="caption" style={{ lineHeight: 1.5 }}>
          No resolved {kind.toLowerCase()} sessions yet, so SiteBrain uses the engineers' likelihoods as written. Every fix a
          field operator confirms with <b>Mark Resolved</b> teaches it how common each cause is here and how each cause answers each check.
        </div>
      ) : (
        <>
          <div className="caption" style={{ lineHeight: 1.5 }}>
            How often each direct cause is the answer at this plant: grey = engineers' starting assumption, green = after learning
            (the engineers' view counts as {d.data.strength} sessions).
          </div>
          {k.causes.map((c) => (
            <div key={c.id} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <div className="row"><span className="caption grow" style={{ color: "var(--t80)" }}>{c.label}</span>
                <span className="caption">{c.sessions} confirmed · {Math.round(c.learned_share * 100)}%</span></div>
              <div className="bar" style={{ position: "relative" }}>
                <div style={{ width: `${(c.learned_share / max) * 100}%`, background: "var(--gps-primary)" }} />
                <span style={{ position: "absolute", left: `${(c.authored_share / max) * 100}%`, top: -2, bottom: -2, width: 2, background: "var(--t40)" }} />
              </div>
            </div>
          ))}
          {k.changes.length > 0 && <div className="overline" style={{ paddingTop: 6 }}>Biggest changes to check evidence</div>}
          {k.changes.map((c, i) => (
            <div key={i} className="caption" style={{ color: "var(--t70)", lineHeight: 1.45, borderBottom: "1px solid var(--t10)", paddingBottom: 4 }}>
              “{c.answer}” for {c.cause.toLowerCase()}: <b>{c.authored}× → <span style={{ color: c.learned > c.authored ? "var(--gps-green-dark)" : "var(--gps-red)" }}>{c.learned}×</span></b>
              <div style={{ color: "var(--t50)" }}>{c.check}</div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function WhyTree({ node, depth = 0 }) {
  if (!node) return null;
  if (node.type === "root") {
    return (
      <div style={{ marginLeft: depth ? 12 : 0, borderLeft: `3px solid ${CAT_COLOR[node.category]}`, padding: "4px 8px", background: "var(--tint)", borderRadius: 4 }}>
        <div className="row" style={{ gap: 6 }}><Icon name="target" size={14} color={CAT_COLOR[node.category]} /><b style={{ fontSize: 13 }}>{node.label}</b><CatChip category={node.category} /></div>
        {node.prevent.map((p, i) => <div key={i} className="caption" style={{ color: "var(--t70)" }}>Prevent: {p}</div>)}
      </div>
    );
  }
  return (
    <div style={{ marginLeft: depth ? 12 : 0, display: "flex", flexDirection: "column", gap: 4 }}>
      <div className="caption" style={{ color: "#1c6fc1", fontWeight: 600 }}>Why? {node.text}</div>
      {node.branches.map((b) => (
        <div key={b.label} style={{ marginLeft: 8, display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 13, color: "var(--t80)" }}>→ {b.label}</div>
          <WhyTree node={b.then} depth={depth + 1} />
        </div>
      ))}
    </div>
  );
}

function Maintenance({ m }) {
  return (
    <div className="card" style={{ gap: 6 }}>
      <div className="card-title">Maintenance knowledge</div>
      <div className="caption" style={{ color: "var(--t70)", lineHeight: 1.5 }}>{m.summary}</div>
      {m.pm?.length > 0 && <div className="overline" style={{ paddingTop: 6 }}>Preventive maintenance</div>}
      {(m.pm || []).map(([when, what], i) => (
        <div key={i} className="row" style={{ alignItems: "flex-start", borderBottom: "1px solid var(--t10)", padding: "4px 0" }}>
          <span className="caption" style={{ minWidth: 90, fontWeight: 600 }}>{when}</span><span className="caption" style={{ color: "var(--t70)" }}>{what}</span>
        </div>
      ))}
      {m.operating_limits?.length > 0 && <div className="overline" style={{ paddingTop: 6 }}>Operating limits</div>}
      {(m.operating_limits || []).map(([p, v], i) => (
        <div key={i} className="row"><span className="caption grow">{p}</span><span className="caption" style={{ fontWeight: 600, color: "var(--gps-green-dark)" }}>{v}</span></div>
      ))}
      {m.failure_modes?.length > 0 && <div className="overline" style={{ paddingTop: 6 }}>Common failure modes</div>}
      {(m.failure_modes || []).map((f, i) => <div key={i} className="caption" style={{ color: "var(--t70)" }}>• {f}</div>)}
    </div>
  );
}

function Conditions() {
  const data = useAsync(() => api.get("/api/kb/conditions"), []);
  if (!data.data) return <Spinner />;
  if (!data.data.length) return <Empty icon="gauge" title="No operating profiles yet" />;
  return data.data.map((p) => (
    <div key={p.id} className="card" style={{ gap: 8 }}>
      <div className="row wrap"><Icon name="gauge" size={20} color="var(--gps-primary)" /><div className="section-title grow">{p.title}</div>
        <span className="caption">{p.areas.join(" · ")}</span></div>
      <div className="table">
        <div style={{ minWidth: 760 }}>
          <div className="trow head" style={{ gridTemplateColumns: "minmax(160px,1.1fr) minmax(120px,0.8fr) minmax(200px,1.5fr) minmax(200px,1.5fr)" }}>
            <span>Parameter</span><span>Normal</span><span>Why it matters</span><span>If out of range</span>
          </div>
          {p.params.map((x) => (
            <div key={x.parameter} className="trow" style={{ gridTemplateColumns: "minmax(160px,1.1fr) minmax(120px,0.8fr) minmax(200px,1.5fr) minmax(200px,1.5fr)" }}>
              <span style={{ color: "var(--t80)", fontWeight: 500 }}>{x.parameter}</span>
              <span style={{ color: "var(--gps-green-dark)", fontWeight: 600 }}>{x.normal}</span>
              <span className="caption" style={{ color: "var(--t70)", lineHeight: 1.45 }}>{x.why}</span>
              <span className="caption" style={{ color: "var(--t70)", lineHeight: 1.45 }}>{x.action}</span>
            </div>
          ))}
        </div>
      </div>
      {p.notes.map((n, i) => <div key={i} className="caption" style={{ color: "var(--t60)" }}>• {n}</div>)}
    </div>
  ));
}

const SOURCE_TABS = [["all", "All Sources"], ["pir", "Historic PIR"], ["rca", "Historic RCA"], ["copilot", "Learned In The App"], ["curated", "Curated"]];
const PAGE = 60;

function Cases({ canWrite, notify }) {
  const [kind, setKind] = useState("All");
  const [source, setSource] = useState("all");
  const [project, setProject] = useState("");
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [limit, setLimit] = useState(PAGE);
  const [adding, setAdding] = useState(false);
  const [open, setOpen] = useState(null);
  const [filters, setFilters] = useState(false);
  useEffect(() => { const t = setTimeout(() => setDq(q), 250); return () => clearTimeout(t); }, [q]);
  useEffect(() => setLimit(PAGE), [kind, source, project, dq]);
  const cases = useAsync(() => api.get(`/api/kb/cases?kind=${encodeURIComponent(kind)}&q=${encodeURIComponent(dq)}`
    + `&source=${source}&project=${encodeURIComponent(project)}&limit=${limit}`), [kind, dq, source, project, limit]);
  const kinds = KINDS;

  return (
    <>
      <div className="row wrap" style={{ gap: 12 }}>
        <div className="search" style={{ flex: "1 1 280px", maxWidth: 420 }}>
          <Icon name="magnify" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search symptom, equipment, root cause or case ID" aria-label="Search cases" />
        </div>
        <select className="select pill" value={project} onChange={(e) => setProject(e.target.value)} aria-label="Project">
          <option value="">All Projects</option>
          {(cases.data?.projects || []).map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <button className={`btn sm ${filters ? "" : "ghost"}`} onClick={() => setFilters((x) => !x)}>
          <Icon name="filter-variant" />Filters{kind !== "All" || source !== "all" ? " · on" : ""}
        </button>
        {canWrite && <button className="btn" onClick={() => setAdding(true)}><Icon name="plus" />Add Verified Case</button>}
      </div>
      {filters && (
        <>
          <PillTabs value={kind} onChange={setKind} options={[["All", "All Equipment"], ...kinds.map((k) => [k, k])]} />
          <PillTabs value={source} onChange={setSource} options={SOURCE_TABS} />
        </>
      )}
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
        <div style={{ flex: "2 1 480px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="row" style={{ alignItems: "baseline" }}>
            <div className="section-title">Past Cases</div>
            {cases.data && <span className="caption">{cases.data.matched} of {cases.data.total} cases</span>}
          </div>
          {!cases.data ? <Spinner /> : cases.data.items.map((k) => (
            <div key={k.id} className="card" style={{ boxShadow: "none", border: "1px solid var(--t10)", gap: 8 }}>
              <div className="row wrap" style={{ gap: 12 }}>
                <span style={{ fontWeight: 600, color: "var(--gps-primary)" }}>{k.id}</span>
                <span className="caption" style={{ color: "var(--t60)" }}>{k.kinds.join(" · ")}</span>
                {k.is_new && <span className="tag" style={{ color: "#006400", background: "#e3f2d4" }}>Learned In The App</span>}
                {k.historic && <span className="tag" style={{ color: "#1c6fc1", background: "#e8f2fd" }}>{k.id.startsWith("RCA-") ? "Historic RCA" : "Historic PIR"}</span>}
                <span className="caption" style={{ marginLeft: "auto" }}>{k.source}</span>
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, color: "var(--t80)" }}>{k.title}</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
                <div><div className="row" style={{ gap: 8 }}><span className="overline">Cause</span></div>
                  <div style={{ lineHeight: 1.5, color: "var(--t80)" }}>{k.cause}</div></div>
                <div><div className="overline">What fixed it</div><div style={{ lineHeight: 1.5, color: "var(--t80)" }}>{k.fix}</div></div>
                {k.prevent && <div><div className="overline">Stop it coming back</div><div style={{ lineHeight: 1.5, color: "var(--t80)" }}>{k.prevent}</div></div>}
              </div>
              {k.why_chain?.length > 0 && (
                <details><summary className="caption" style={{ cursor: "pointer", color: "#1c6fc1", fontWeight: 600 }}>How they got to the cause</summary>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4, paddingTop: 6 }}>
                    {k.why_chain.map((w, i) => <div key={i} className="caption" style={{ color: "var(--t70)" }}>{i + 1}. {w}</div>)}
                  </div>
                </details>
              )}
              {k.historic && <button className="btn ghost sm" style={{ alignSelf: "flex-start" }} onClick={() => setOpen(k.id)}><Icon name="file-document-outline" />Full Report</button>}
            </div>
          ))}
          {cases.data && cases.data.matched > cases.data.items.length && (
            <button className="btn ghost" style={{ alignSelf: "center" }} onClick={() => setLimit((n) => n + PAGE)}>
              Show More ({cases.data.matched - cases.data.items.length} left)
            </button>
          )}
          {cases.data && !cases.data.items.length && (
            <Empty icon="book-search-outline" title="No Matching Cases">
              Change the search, or pick <b style={{ color: "var(--gps-primary)" }}>All Types</b> to see every case.
            </Empty>
          )}
        </div>
      </div>
      {open && <ReportModal id={open} onClose={() => setOpen(null)} />}
      {adding && <AddCase onClose={() => setAdding(false)} onSaved={(id) => { setAdding(false); notify(`Saved as ${id}`); cases.reload(); }} notify={notify} />}
    </>
  );
}

// Every field SiteBrain read from a historic PIR / RCA report, and the file it came from
function ReportModal({ id, onClose }) {
  const d = useAsync(() => api.get(`/api/kb/cases/${id}`), [id]);
  const r = d.data?.report;
  const facts = r && [["Project", r.project], ["Document No.", r.doc_no], ["PIR Reference", r.pir_ref], ["Date", r.date],
    ["Equipment", r.equipment], ["Area / Unit", r.unit], ["Failure Type", r.failure_type], ["Severity", r.severity],
    ["Repeat Failure", r.repeat], ["Impact On Feeding / CBG", r.impact], ["Downtime", r.downtime]].filter(([, v]) => v);
  const block = (label, v) => v && (Array.isArray(v) ? v.length > 0 : true) && (
    <div key={label}><div className="overline">{label}</div>
      {Array.isArray(v) ? <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>{v.map((x, i) => <li key={i} style={{ lineHeight: 1.5 }}>{x}</li>)}</ul>
        : <div style={{ lineHeight: 1.5, color: "var(--t80)", whiteSpace: "pre-wrap" }}>{v}</div>}</div>
  );
  return (
    <Modal title={d.data ? `${id} · ${r?.title || d.data.title}` : id} onClose={onClose} width={760}>
      {!d.data ? <Spinner /> : (
        <>
          <div className="caption">{r?.type} report · {d.data.file}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}>
            {(facts || []).map(([k, v]) => <div key={k}><div className="overline">{k}</div><div>{v}</div></div>)}
          </div>
          {block("Incident Description", r?.description)}
          {block("What Went Wrong", r?.what_went_wrong)}
          {block("Immediate Action Taken", r?.immediate_action)}
          {block("5-Why", r?.why_chain)}
          {block("Root Cause", r?.root_cause)}
          {block("Corrective Actions", r?.corrective)}
          {block("Preventive Actions", r?.preventive)}
          {block("Conclusion", r?.conclusion)}
        </>
      )}
    </Modal>
  );
}

function AddCase({ onClose, onSaved, notify }) {
  const [f, setF] = useState({ kinds: ["Pump"], title: "", cause: "", fix: "", keys: "" });
  const save = async () => {
    try {
      const r = await api.post("/api/kb/cases", { ...f, keys: f.keys.split(",").map((s) => s.trim()).filter(Boolean) });
      onSaved(r.id);
    } catch (e) {
      notify(e.message, true);
    }
  };
  return (
    <Modal title="Add verified case (model calibration)" onClose={onClose} width={560}>
      <select className="select" value={f.kinds[0]} onChange={(e) => setF({ ...f, kinds: [e.target.value] })} aria-label="Equipment type">
        {KINDS.map((k) => <option key={k}>{k}</option>)}
      </select>
      <input className="input" placeholder="Symptom / abnormality" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
      <input className="input" placeholder="Root cause" value={f.cause} onChange={(e) => setF({ ...f, cause: e.target.value })} />
      <textarea className="textarea" rows={3} placeholder="Verified resolution" value={f.fix} onChange={(e) => setF({ ...f, fix: e.target.value })} />
      <input className="input" placeholder="Symptom keywords, comma separated (e.g. vibration, seal)" value={f.keys} onChange={(e) => setF({ ...f, keys: e.target.value })} />
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn" onClick={save} disabled={!f.title || !f.cause || !f.fix}>Save Case</button>
      </div>
    </Modal>
  );
}

function Docs({ canWrite, notify }) {
  const docs = useAsync(() => api.get("/api/kb/documents"), []);
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  const [asking, setAsking] = useState(false);
  const [file, setFile] = useState(null);
  const [kind, setKind] = useState("manual");
  const [title, setTitle] = useState("");
  const [eqKind, setEqKind] = useState("");
  const [uploading, setUploading] = useState(false);

  const search = async (e) => {
    e.preventDefault();
    if (!q.trim()) return;
    setAsking(true);
    try { setRes(await api.get(`/api/kb/ask?q=${encodeURIComponent(q)}`)); } catch (er) { notify(er.message, true); }
    finally { setAsking(false); }
  };
  const upload = async () => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", title);
    fd.append("kind", kind);
    fd.append("equipment_kind", eqKind);
    setUploading(true);
    try {
      const r = await api.post("/api/kb/documents", fd);
      notify(`Indexed “${r.title}”: ${r.chunks} chunks${r.cases_added ? `, ${r.cases_added} cases imported` : ""} · ${r.equipment_kinds.length ? r.equipment_kinds.join(", ") : "general (all equipment)"}${r.tagged_by === "llm" ? " (read by AI)" : ""}`);
      setFile(null); setTitle(""); setEqKind("");
      docs.reload();
    } catch (er) {
      notify(er.message, true);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
      <div style={{ flex: "2 1 480px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
        <form className="search" onSubmit={search}>
          <Icon name="text-search" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask the manuals: e.g. what is the dew point limit after the chiller?" aria-label="Ask the documents" />
          <button className="btn sm" type="submit" disabled={asking}>{asking ? <Icon name="loading" className="spin" /> : "Ask"}</button>
        </form>
        {res?.answer && (
          <div className="card">
            <div className="card-title"><Icon name="creation" /> Answer</div>
            <div style={{ whiteSpace: "pre-wrap" }}>{res.answer}</div>
            {res.hits.some((h) => h.cited) && (
              <div className="caption" style={{ color: "var(--t60)" }}>
                Sources: {[...new Set(res.hits.filter((h) => h.cited).map((h) => h.title))].join(" · ")}
              </div>
            )}
          </div>
        )}
        {res && (
          <div className="card">
            <div className="card-title">{res.hits.length} passages{res.llm ? ` · ${res.hits.filter((h) => h.cited).length} used in the answer` : ""}</div>
            {res.hits.map((h, i) => (
              <div key={i} style={{ borderBottom: "1px solid var(--t10)", paddingBottom: 8, opacity: res.llm && !h.cited ? 0.6 : 1 }}>
                <div className="row"><b style={{ color: "var(--gps-primary)" }}>{h.cited && <Icon name="check-circle-outline" />} {h.title}</b><span className="caption">{h.kind} · {h.equipment_kinds?.length ? h.equipment_kinds.join(", ") : "general"} · relevance {h.score}%</span></div>
                <div className="caption" style={{ whiteSpace: "pre-wrap", color: "var(--t70)" }}>{h.excerpt}</div>
              </div>
            ))}
            {!res.hits.length && <div className="caption">No passages match.</div>}
          </div>
        )}
        <div className="section-title">Indexed Documents</div>
        <div className="table">
          <div className="trow head" style={{ gridTemplateColumns: "minmax(200px,2fr) minmax(120px,1fr) 90px 80px 120px 110px" }}>
            <span>Title</span><span>Equipment</span><span>Type</span><span>Chunks</span><span>Added by</span><span>Date</span>
          </div>
          {(docs.data || []).map((d) => (
            <div key={d.id} className="trow" style={{ gridTemplateColumns: "minmax(200px,2fr) minmax(120px,1fr) 90px 80px 120px 110px" }}>
              <span><Icon name="file-document-outline" color="var(--t60)" /> {d.title}
                {d.summary && <div className="caption" style={{ color: "var(--t60)" }}>{d.summary}</div>}</span>
              <span className="caption" title={{ llm: "Read by AI", uploader: "Set at upload", keywords: "Detected from keywords" }[d.tagged_by] || ""}>
                {d.equipment_kinds?.length ? d.equipment_kinds.join(" · ") : "General"}{d.tagged_by === "llm" ? " ✦" : ""}
              </span>
              <span className="caption" style={{ textTransform: "uppercase" }}>{d.kind}</span>
              <span>{d.chunk_count}</span>
              <span className="muted">{d.uploaded_by}</span>
              <span className="caption">{fmtDate(d.created_at)}</span>
            </div>
          ))}
        </div>
      </div>
      <div style={{ flex: "1 1 300px", minWidth: 0 }}>
        <div className="card">
          <div className="card-title">Knowledge Ingestion</div>
          <div className="caption">Batch-ingest OEM manuals (PDF), SOPs and reports (Word/TXT/MD), spreadsheets (XLSX) and incident logs (CSV with symptom, root cause and resolution columns become cases).</div>
          {canWrite ? (
            <>
              <input type="file" accept=".pdf,.docx,.txt,.md,.csv,.xlsx" onChange={(e) => setFile(e.target.files[0] || null)} aria-label="Document file" />
              <input className="input" placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
              <select className="select" value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Document type">
                <option value="manual">OEM manual</option><option value="sop">SOP</option><option value="log">Incident / shift log</option>
              </select>
              <select className="select" value={eqKind} onChange={(e) => setEqKind(e.target.value)} aria-label="Equipment type">
                <option value="">Equipment: detect from content</option>
                {KINDS.filter((k) => k !== "Machine").map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
              <button className="btn" disabled={!file || uploading} onClick={upload}>
                {uploading ? <><Icon name="loading" className="spin" />Indexing…</> : <><Icon name="upload" />Upload & Index</>}
              </button>
            </>
          ) : <div className="caption" style={{ color: "var(--t60)" }}>Only L2/L3 experts can ingest documents.</div>}
        </div>
      </div>
    </div>
  );
}
