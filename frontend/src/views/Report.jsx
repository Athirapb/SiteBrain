import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Icon, Spinner } from "../components/ui";
import { AttachMenu, FileChips, VoiceNotePanel, filesForm, useFiles } from "../components/media";
import SearchSelect from "../components/SearchSelect";

export const SEV_TONE = { Low: "#868686", Medium: "#3191ef", High: "#ffa500", Critical: "#f5524a" };
const LAST = "sb.lastReport"; // the place of the last report, the fallback prefill
const SHOW_SYMPTOMS_SEVERITY = false; // "What do you notice" / "How serious" hidden for now; severity stays at its default

function lastPlace() {
  try { return JSON.parse(localStorage.getItem(LAST) || "{}"); } catch { return {}; }
}

// Report An Issue: where (prefilled from the user's profile) and what, with photos, videos and voice notes
export default function Report({ meta, user, equipment, nav, notify, refreshShared }) {
  const [projects, setProjects] = useState(null);
  const [areas, setAreas] = useState(null);
  const [projectId, setProjectId] = useState("");
  const [areaId, setAreaId] = useState("");
  const [eqId, setEqId] = useState("");
  const [symptoms, setSymptoms] = useState([]);
  const [severity, setSeverity] = useState("Medium");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(0); // voice notes being transcribed
  const media = useFiles(notify);

  // a voice note becomes the written description (any language; the English version is used), ready to edit
  const addMedia = (files) => {
    media.add(files);
    if (!meta.media) return;
    files.filter((f) => (f.type || "").startsWith("audio/")).forEach(async (f) => {
      setListening((n) => n + 1);
      try {
        const fd = new FormData();
        fd.append("file", f);
        fd.append("options", JSON.stringify(fitting.map((sy) => sy.label)));
        fd.append("multi", "true");
        const t = await api.post("/api/sessions/transcribe", fd);
        const said = (t.english || t.text || "").trim();
        if (said) setDescription((d) => (d.trim() ? `${d.trim()} ${said}` : said));
        const ids = fitting.filter((sy) => (t.matches || []).includes(sy.label)).map((sy) => sy.id);
        if (ids.length) setSymptoms((cur) => [...new Set([...cur, ...ids])]);
        notify(t.english && t.english !== t.text ? `Voice note transcribed and translated from ${t.language}` : "Voice note added to the description");
      } catch (e) {
        notify(e.message, true);
      } finally {
        setListening((n) => n - 1);
      }
    });
  };

  useEffect(() => {
    api.get("/api/areas").then(setAreas).catch(() => setAreas([]));
    api.get("/api/projects").then(setProjects).catch(() => setProjects([]));
  }, []);
  // prefill: the user's profile first, else the place of their last report
  useEffect(() => {
    if (!areas || !projects) return;
    const last = lastPlace();
    const pid = user.project_id || last.projectId;
    if (pid && projects.some((p) => p.id === pid)) setProjectId(pid);
    const byCode = user.area_code && areas.find((a) => a.code === user.area_code);
    const a = byCode || areas.find((x) => x.id === last.areaId);
    if (a) setAreaId(a.id);
    if (!byCode && a && last.equipmentId) setEqId(last.equipmentId);
  }, [areas, projects, user]);

  const areaEq = equipment.filter((e) => String(e.area_id) === String(areaId));
  const chosen = equipment.find((e) => e.id === eqId);
  const kinds = new Set(chosen ? [chosen.kind] : areaEq.map((e) => e.kind));
  const fitting = !areaId ? [] : meta.symptoms.filter((sy) => !kinds.size || sy.kinds.some((k) => kinds.has(k)));
  const fitKey = fitting.map((sy) => sy.id).join();
  useEffect(() => {
    setSymptoms((cur) => cur.filter((id) => fitting.some((sy) => sy.id === id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey]);
  const toggle = (id) => setSymptoms((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  const ready = projectId && areaId && eqId && (symptoms.length || description.trim()) && !media.tooBig.length && !listening;
  const prefilled = useMemo(() => !!(user.project_id || user.area_code), [user]);

  const submit = async () => {
    setBusy(true);
    try {
      const v = await api.post("/api/sessions", { project_id: projectId, area_id: areaId, equipment_id: eqId,
                                                  symptoms, severity, description });
      try { localStorage.setItem(LAST, JSON.stringify({ projectId, areaId, equipmentId: eqId || null })); } catch {}
      if (media.files.length) {
        try {
          await api.post(`/api/sessions/${v.session.id}/files`, filesForm(media.files, { caption: "Photos and recordings from the issue report" }));
        } catch (e) { notify(`The report is in, but the files didn't upload: ${e.message}`, true); }
      }
      refreshShared();
      nav("issue", { sessionId: v.session.id, from: "issues" });
    } catch (e) {
      notify(e.message, true);
      setBusy(false);
    }
  };

  if (!areas || !projects) return <div className="page"><Spinner /></div>;
  return (
    <div className="page narrow">
      <div>
        <div className="page-title">Report An Issue</div>
        <div className="page-sub">Tell SiteBrain where the problem is and what you notice. It will guide you to the cause step by step.</div>
      </div>

      <section className="card form-card">
        <div className="form-card-head"><span className="form-step">1</span><div className="section-title">Where is the issue?</div>
          {prefilled && <span className="caption" style={{ marginLeft: "auto" }}><Icon name="auto-fix" size={14} /> Filled in from your profile</span>}</div>
        <label className="field">
          <span className="overline">Project</span>
          <SearchSelect className="select lg" value={projectId} onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Select the project…</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}{p.name !== p.code ? ` (${p.code})` : ""}</option>)}
          </SearchSelect>
        </label>
        <label className="field">
          <span className="overline">Area</span>
          <SearchSelect className="select lg" value={areaId} onChange={(e) => { setAreaId(e.target.value ? Number(e.target.value) : ""); setEqId(""); }}>
            <option value="">Select the area…</option>
            {areas.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.code})</option>)}
          </SearchSelect>
        </label>
        <label className="field">
          <span className="overline">Equipment</span>
          <SearchSelect className="select lg" value={eqId} disabled={!areaId} onChange={(e) => setEqId(e.target.value)}>
            <option value="">{areaId ? "Select the equipment…" : "Pick the area first…"}</option>
            {areaEq.map((e) => <option key={e.id} value={e.id}>{e.name} · {e.kind}{e.tag ? ` · ${e.tag}` : ""}</option>)}
          </SearchSelect>
        </label>
        {chosen?.open_session_id && (
          <div className="safety" style={{ alignItems: "center" }}>
            <Icon name="information-outline" />
            <div className="grow">{chosen.name} already has an open issue ({chosen.open_session_id}).</div>
            <button className="btn ghost sm" onClick={() => nav("issue", { sessionId: chosen.open_session_id, from: "issues" })}>Open It</button>
          </div>
        )}
      </section>

      <section className="card form-card">
        <div className="form-card-head"><span className="form-step">2</span><div className="section-title">What issue are you facing?</div></div>
        <div className="form-intro">Tell us what's happening. You can type, record a voice note or share photos/videos to help us understand the issue.</div>
        {SHOW_SYMPTOMS_SEVERITY && <>
        <div className="field">
          <span className="overline">What do you notice</span>
          {!areaId && <div className="caption">Pick the area first to see what you can report.</div>}
          <div className="row wrap" style={{ gap: 8 }}>
            {fitting.map((sy) => (
              <button key={sy.id} className={`opt lg ${symptoms.includes(sy.id) ? "on" : ""}`} aria-pressed={symptoms.includes(sy.id)}
                      onClick={() => toggle(sy.id)}>
                <Icon name={sy.icon} /> {sy.label}
              </button>
            ))}
          </div>
        </div>
        <div className="field">
          <span className="overline">How serious</span>
          <div className="row wrap" style={{ gap: 8 }}>
            {meta.severities.map((sv) => (
              <button key={sv} className="opt lg" aria-pressed={severity === sv} onClick={() => setSeverity(sv)}
                      style={severity === sv ? { background: SEV_TONE[sv], color: "#fff", borderColor: SEV_TONE[sv], fontWeight: 600 } : undefined}>
                {sv}
              </button>
            ))}
          </div>
          <div className="caption">Critical: stop-the-plant risk (heavy vibration, gas leak, smoke).</div>
        </div>
        </>}
        <div className="field">
          <label className="field-label" htmlFor="issue-desc">Describe the issue</label>
          <div className="desc-box">
            <textarea id="issue-desc" className="textarea" rows={3} value={description} onChange={(e) => setDescription(e.target.value)}
                      placeholder="Type your issue here... Include what happened and where you noticed it." />
            <span className="input-badge">Text input</span>
          </div>
        </div>
        <div className="field">
          <div className="field-label"><Icon name="microphone-outline" size={18} className="label-icon" />Prefer speaking?</div>
          <div className="form-hint">Record a voice note in your preferred language. We'll convert it into text for you.</div>
          <VoiceNotePanel onFile={(f) => addMedia([f])} onError={(m) => notify(m, true)}
                          disabled={media.files.length >= 5} busy={listening > 0} />
        </div>
        <hr className="form-divider" />
        <div className="field">
          <div className="field-label"><Icon name="paperclip" size={18} className="label-icon" />Add photos or videos <span className="optional">(Optional)</span></div>
          <div className="form-hint">Have a photo or video showing the issue? Attach it here to help us understand better.</div>
          <AttachMenu block label="Attach Photos / Videos / Files" onFiles={addMedia} disabled={media.files.length >= 5} />
          <FileChips files={media.files} onRemove={media.remove} />
          <div className="caption">You can skip this if you don't have any attachments.</div>
        </div>
        {!ready && <div className="caption form-status">{!projectId ? "Pick the project above." : !areaId ? "Pick the area above." : !eqId ? "Pick the equipment above."
          : media.tooBig.length ? "A file is over 10 MB." : listening ? "Listening to your voice note…"
          : !ready ? "Describe the issue or record a voice note to continue." : ""}</div>}
        <button className="btn lg block start-btn" disabled={!ready || busy} onClick={submit}>
          {busy ? "Starting…" : "Start Troubleshooting"} <Icon name="arrow-right" />
        </button>
      </section>

    </div>
  );
}
