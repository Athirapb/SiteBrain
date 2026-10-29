// Multimedia-first reporting: take a photo, record a video or a voice note, or pick a file. Nothing is analysed in
// this version; the files go into the issue and to the expert.
import { useEffect, useRef, useState } from "react";
import { FILE_ICON, Icon, fmtSize } from "./ui";

export const MAX_FILES = 5;
export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const FILE_TYPES = "image/*,video/*,audio/*,.pdf,.txt,.csv,.xlsx,.xls,.docx,.doc";

const stamp = () => new Date().toTimeString().slice(0, 8).replace(/:/g, "");

// Records from the microphone with MediaRecorder (free, in the browser); onDone gets an audio File.
// maxSeconds stops the recording by itself (a spoken answer is short).
export function useVoiceNote(onDone, onError, maxSeconds = 0) {
  const [rec, setRec] = useState(null); // {recorder, stream, started}
  const [secs, setSecs] = useState(0);
  const chunks = useRef([]);
  useEffect(() => {
    if (!rec) return undefined;
    const id = setInterval(() => {
      const n = Math.round((Date.now() - rec.started) / 1000);
      setSecs(n);
      if (maxSeconds && n >= maxSeconds && rec.recorder.state === "recording") { rec.recorder.stop(); setRec(null); }
    }, 500);
    return () => clearInterval(id);
  }, [rec, maxSeconds]);
  useEffect(() => () => rec?.stream.getTracks().forEach((t) => t.stop()), [rec]);

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onError?.("Voice notes need a browser with microphone access");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunks.current = [];
      recorder.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      recorder.onstop = () => {
        const type = recorder.mimeType || "audio/webm";
        const ext = type.includes("ogg") ? "ogg" : type.includes("mp4") ? "m4a" : "webm";
        const blob = new Blob(chunks.current, { type });
        stream.getTracks().forEach((t) => t.stop());
        if (blob.size) onDone(new File([blob], `voice-note-${stamp()}.${ext}`, { type }));
      };
      recorder.start();
      setSecs(0);
      setRec({ recorder, stream, started: Date.now() });
    } catch {
      onError?.("Microphone access was blocked. Allow it in the browser to record a voice note.");
    }
  };
  const stop = () => {
    if (rec?.recorder.state === "recording") rec.recorder.stop();
    setRec(null);
  };
  const cancel = () => {
    if (rec) {
      rec.recorder.onstop = () => rec.stream.getTracks().forEach((t) => t.stop());
      if (rec.recorder.state === "recording") rec.recorder.stop();
    }
    setRec(null);
  };
  return { recording: !!rec, secs, start, stop, cancel };
}

const fmtSecs = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

// The row of big capture buttons: Take Photo · Record Video · Voice Note · Add File
export function MediaButtons({ onFiles, onError, disabled, full = true, compact = false }) {
  const voice = useVoiceNote((f) => onFiles([f]), onError);
  const pick = (e) => { onFiles(Array.from(e.target.files || [])); e.target.value = ""; };
  if (voice.recording) {
    return (
      <div className="recording">
        <span className="rec-dot" /> Recording voice note · {fmtSecs(voice.secs)}
        <span className="grow" />
        <button className="btn ghost sm" onClick={voice.cancel}>Cancel</button>
        <button className="btn sm" onClick={voice.stop}><Icon name="stop" />Stop & Attach</button>
      </div>
    );
  }
  const btn = (icon, label, input) => (
    <label className={`media-btn ${compact ? "compact" : ""} ${disabled ? "disabled" : ""}`} title={label}>
      <Icon name={icon} />
      <span>{label}</span>
      {input}
    </label>
  );
  return (
    <div className={`media-row ${compact ? "compact" : ""}`}>
      {btn("camera-outline", "Take Photo",
        <input type="file" hidden accept="image/*" capture="environment" disabled={disabled} onChange={pick} />)}
      {btn("video-outline", "Record Video",
        <input type="file" hidden accept="video/*" capture="environment" disabled={disabled} onChange={pick} />)}
      <button type="button" className={`media-btn ${compact ? "compact" : ""}`} disabled={disabled} onClick={voice.start} title="Voice Note">
        <Icon name="microphone-outline" /><span>Voice Note</span>
      </button>
      {full && btn("paperclip", "Add File",
        <input type="file" hidden multiple accept={FILE_TYPES} disabled={disabled} onChange={pick} />)}
    </div>
  );
}

// One Attach button: Take Photo · Record Video · Choose File in a small menu
export function AttachMenu({ onFiles, disabled }) {
  const [open, setOpen] = useState(false);
  const pick = (e) => { setOpen(false); onFiles(Array.from(e.target.files || [])); e.target.value = ""; };
  const item = (icon, label, input) => (
    <label className="menu-item"><Icon name={icon} />{label}{input}</label>
  );
  return (
    <div className="menu-wrap" onMouseLeave={() => setOpen(false)}>
      <button type="button" className="btn ghost" disabled={disabled} aria-expanded={open} onClick={() => setOpen((x) => !x)}>
        <Icon name="paperclip" />Attach File<Icon name={open ? "chevron-up" : "chevron-down"} size={16} />
      </button>
      {open && !disabled && (
        <div className="menu left">
          {item("camera-outline", "Take Photo", <input type="file" hidden accept="image/*" capture="environment" onChange={pick} />)}
          {item("video-outline", "Record Video", <input type="file" hidden accept="video/*" capture="environment" onChange={pick} />)}
          {item("file-upload-outline", "Choose File", <input type="file" hidden multiple accept={FILE_TYPES} onChange={pick} />)}
        </div>
      )}
    </div>
  );
}

// A round mic button that records a voice note; while recording it shows the timer, Cancel and Stop
export function VoiceNoteButton({ onFile, onError, disabled }) {
  const voice = useVoiceNote(onFile, onError);
  if (voice.recording) {
    return (
      <div className="recording voice-inline">
        <span className="rec-dot" />{fmtSecs(voice.secs)}
        <button type="button" className="btn ghost sm" onClick={voice.cancel}>Cancel</button>
        <button type="button" className="btn sm" onClick={voice.stop}><Icon name="stop" />Stop</button>
      </div>
    );
  }
  return (
    <button type="button" className="send-btn" disabled={disabled} onClick={voice.start} aria-label="Record a voice note" title="Record a voice note">
      <Icon name="microphone" size={22} />
    </button>
  );
}

// Files waiting to be sent, as removable chips (an over-size one is flagged)
export function FileChips({ files, onRemove }) {
  if (!files.length) return null;
  return (
    <div className="row wrap" style={{ gap: 8 }}>
      {files.map((f, i) => (
        <span key={`${f.name}-${i}`} className={`file-chip ${f.size > MAX_FILE_BYTES ? "bad" : ""}`}
              title={f.size > MAX_FILE_BYTES ? "Over 10 MB — remove it to send" : f.name}>
          <Icon name={FILE_ICON(f.type || "", f.name)} size={16} />
          <span className="file-chip-name">{f.name}</span>
          <span className="caption">{fmtSize(f.size)}</span>
          <button aria-label={`Remove ${f.name}`} onClick={() => onRemove(i)}><Icon name="close" size={14} /></button>
        </span>
      ))}
    </div>
  );
}

// Keeps a list of picked files within the limits
export function useFiles(notify) {
  const [files, setFiles] = useState([]);
  const add = (list) => {
    const picked = Array.from(list || []);
    if (!picked.length) return;
    setFiles((cur) => {
      const next = [...cur, ...picked];
      if (next.length > MAX_FILES) notify?.(`Attach up to ${MAX_FILES} files at a time`, true);
      return next.slice(0, MAX_FILES);
    });
  };
  const remove = (i) => setFiles((cur) => cur.filter((_, j) => j !== i));
  const tooBig = files.filter((f) => f.size > MAX_FILE_BYTES);
  return { files, add, remove, clear: () => setFiles([]), tooBig };
}

export const filesForm = (files, fields = {}) => {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
  files.forEach((f) => fd.append("files", f));
  return fd;
};
