import { useEffect, useRef, useState } from "react";
import { api } from "../api";

export const Icon = ({ name, size, color, className = "", style }) => (
  <i className={`mdi mdi-${name} ${className}`} style={{ fontSize: size, color, ...style }} />
);

export const SEV = {
  ok: ["#e3f2d4", "#006400"],
  warn: ["#fff7e6", "#b36b00"],
  crit: ["#fdeceb", "#d93a32"],
  none: ["#f2f2f2", "#6d6d6d"],
};

export const STATUS_COLOR = {
  Normal: "#28a745",
  Abnormal: "#ffa500",
  Critical: "#f5524a",
  "No data": "#868686",
};

export const URGENCY_BG = { Critical: "#f5524a", High: "#ffa500", Medium: "#3191ef", Low: "#868686" };

export function Empty({ icon = "check-circle-outline", title, children }) {
  return (
    <div className="empty">
      <Icon name={icon} />
      <div style={{ fontSize: 14 }}>{title}</div>
      {children && <div style={{ fontSize: 14, color: "var(--t60)" }}>{children}</div>}
    </div>
  );
}

export function Spinner({ text }) {
  return (
    <div className="row" style={{ color: "var(--t50)", padding: 16 }}>
      <Icon name="loading" className="spin" size={20} color="var(--gps-primary)" />
      <span>{text || "Loading…"}</span>
    </div>
  );
}

export function PillTabs({ value, onChange, options, stretch }) {
  return (
    <div className={stretch ? "row" : "pill-row"} style={stretch ? { gap: 8 } : undefined}>
      {options.map(([v, label]) => (
        <button key={v} className={`pill-tab ${value === v ? "active" : ""}`} onClick={() => onChange(v)}>
          {label}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value, unit, hint }) {
  return (
    <div className="card" style={{ gap: 4 }}>
      <div className="overline">{label}</div>
      <div className="stat-value">
        {value ?? "—"}
        {unit && value != null && <span className="stat-unit">{unit}</span>}
      </div>
      {hint && <div className="caption">{hint}</div>}
    </div>
  );
}

export function Modal({ title, onClose, children, width }) {
  useEffect(() => {
    const k = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={width ? { maxWidth: width } : undefined} role="dialog" aria-label={title}>
        <div className="row">
          <div className="section-title grow">{title}</div>
          <button className="btn ghost sm" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function usePoll(fn, ms, deps) {
  const saved = useRef(fn);
  saved.current = fn;
  useEffect(() => {
    if (!ms) return undefined;
    const id = setInterval(() => saved.current(), ms);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, ...deps]);
}

export function useAsync(loader, deps) {
  const [state, set] = useState({ data: null, error: null, loading: true });
  const reload = useRef(() => {});
  reload.current = () =>
    loader()
      .then((data) => set({ data, error: null, loading: false }))
      .catch((error) => set((s) => ({ ...s, error, loading: false })));
  useEffect(() => {
    set((s) => ({ ...s, loading: true }));
    reload.current();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { ...state, reload: () => reload.current() };
}

export const fmtTime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
};

export const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "—";

export const fmtDuration = (min) => {
  if (min == null) return "—";
  if (min < 60) return `${Math.max(1, Math.round(min))} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m ? `${h} h ${m} min` : `${h} h`;
};

export const fmtSize = (bytes) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;

export const FILE_ICON = (type, name = "") => (type.startsWith("image/") ? "file-image-outline" : type.startsWith("video/") ? "file-video-outline"
  : type.startsWith("audio/") ? "file-music-outline" : type === "application/pdf" ? "file-pdf-box"
  : /sheet|excel|csv/.test(type) || /\.(xlsx?|csv)$/i.test(name) ? "file-excel-outline"
  : /word/.test(type) || /\.docx?$/i.test(name) ? "file-word-outline" : "file-document-outline");

// An attachment (escalation file, or a file shared in the chat via `path`): images show a thumbnail; click opens
// (or downloads) the file
export function Attachment({ ticket, file, path: filePath }) {
  const [url, setUrl] = useState(null);
  const isImage = file.content_type.startsWith("image/") && !file.content_type.includes("svg");
  const path = filePath || `/api/escalations/${ticket}/attachments/${file.id}`;
  useEffect(() => {
    if (!isImage || !file.id) return undefined;
    let u = null;
    api.blob(path).then((b) => { u = URL.createObjectURL(b); setUrl(u); }).catch(() => {});
    return () => u && URL.revokeObjectURL(u);
  }, [path, isImage, file.id]);
  const open = async () => {
    try {
      const u = url || URL.createObjectURL(await api.blob(path));
      const a = document.createElement("a");
      a.href = u;
      a.target = "_blank";
      a.rel = "noopener";
      if (!isImage && !/^(video|audio)\/|^application\/pdf$|^text\/plain$/.test(file.content_type)) a.download = file.filename;
      a.click();
    } catch { /* unavailable: nothing to open */ }
  };
  return (
    <button className="attachment" onClick={open} title={`Open ${file.filename}`}>
      {url ? <img src={url} alt={file.filename} /> : <Icon name={FILE_ICON(file.content_type, file.filename)} size={22} color="var(--t60)" />}
      <span className="attachment-name">{file.filename}</span>
      <span className="caption">{fmtSize(file.size)}</span>
    </button>
  );
}
