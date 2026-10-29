"""Reading what the field operator attaches: voice notes, photos, videos and documents.

Only while SiteBrain is troubleshooting (an escalated issue goes to the expert as it is). Voice notes are
transcribed (Whisper; any language, with an English version for the engine), photos are described by a vision model
that also says which answer of the pending check they show, videos give a few frames plus their soundtrack, and
documents give their text. Everything runs on the OpenAI-compatible API in .env (Groq by default, free tier).
A failure never blocks the chat: the file is kept and the operator is asked to describe it.
"""
import base64
import io
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from . import config, llm

log = logging.getLogger("sitebrain.media")

MAX_FRAMES = 3
MIN_CONFIDENCE = 0.6  # below this a photo's answer is only a hint, never taken as the answer
_client = None


def enabled() -> bool:
    return config.MEDIA_ENABLED and bool(config.MEDIA_API_KEY)


def _api():
    global _client
    if _client is None:
        import openai
        _client = openai.OpenAI(api_key=config.MEDIA_API_KEY, base_url=config.MEDIA_BASE_URL, timeout=90.0, max_retries=1)
    return _client


def kind_of(content_type: str, filename: str = "") -> str | None:
    t = (content_type or "").split(";")[0].lower()
    name = filename.lower()
    if t.startswith("audio/") or (name.endswith((".ogg", ".m4a", ".mp3", ".wav", ".opus")) and not t.startswith("video/")):
        return "audio"
    if t.startswith("image/") and "svg" not in t:
        return "image"
    if t.startswith("video/"):
        return "video"
    if t == "application/pdf" or name.endswith(".pdf"):
        return "pdf"
    if t.startswith("text/") or name.endswith((".txt", ".csv")):
        return "text"
    if "sheet" in t or "excel" in t or name.endswith((".xlsx", ".xls")):
        return "sheet"
    return None


# ---------------------------------------------------------------------------
# ffmpeg (bundled with imageio-ffmpeg): shrink photos, pull frames and sound out of videos
# ---------------------------------------------------------------------------

def _ffmpeg() -> str | None:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - not installed or no binary for this platform
        return None


def _run(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, timeout=timeout)


def _jpeg(data: bytes, width: int = 1280) -> bytes:
    """A photo as a JPEG at most `width` wide (vision APIs cap the upload size); the original when ffmpeg can't."""
    ff = _ffmpeg()
    if not ff:
        return data
    with tempfile.TemporaryDirectory() as d:
        src, out = Path(d) / "in", Path(d) / "out.jpg"
        src.write_bytes(data)
        r = _run([ff, "-v", "error", "-y", "-i", str(src), "-vf", f"scale='min({width},iw)':-2", "-frames:v", "1",
                  "-q:v", "4", str(out)])
        return out.read_bytes() if r.returncode == 0 and out.exists() else data


def _video_parts(data: bytes) -> tuple[list[bytes], bytes | None, float | None]:
    """A few evenly spaced frames (JPEG) and the soundtrack (MP3, mono 16 kHz) of a video, and its length in s."""
    ff = _ffmpeg()
    if not ff:
        return [], None, None
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "in"
        src.write_bytes(data)
        probe = _run([ff, "-i", str(src)], timeout=30)
        m = re.search(rb"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr)
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None
        frames = []
        for i in range(MAX_FRAMES):
            at = (dur or 3) * (i + 0.5) / MAX_FRAMES
            out = Path(d) / f"f{i}.jpg"
            r = _run([ff, "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1",
                      "-vf", "scale='min(960,iw)':-2", "-q:v", "5", str(out)])
            if r.returncode == 0 and out.exists():
                frames.append(out.read_bytes())
        audio = Path(d) / "a.mp3"
        r = _run([ff, "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(audio)])
        sound = audio.read_bytes() if r.returncode == 0 and audio.exists() and audio.stat().st_size > 2000 else None
        return frames, sound, dur


def _tile(frames: list[bytes]) -> bytes:
    """Video frames side by side in one image: one vision call, and a third of the image tokens (the free tier
    limits tokens per minute)."""
    ff = _ffmpeg()
    if not ff or len(frames) < 2:
        return frames[0]
    with tempfile.TemporaryDirectory() as d:
        for i, f in enumerate(frames):
            (Path(d) / f"f{i}.jpg").write_bytes(f)
        out = Path(d) / "tile.jpg"
        r = _run([ff, "-v", "error", "-y", "-i", str(Path(d) / "f%d.jpg"), "-vf", f"scale=480:-2,tile={len(frames)}x1",
                  "-frames:v", "1", "-q:v", "4", str(out)])
        return out.read_bytes() if r.returncode == 0 and out.exists() else frames[len(frames) // 2]


# ---------------------------------------------------------------------------
# The three readers
# ---------------------------------------------------------------------------

def transcribe(data: bytes, filename: str, context: str = "") -> dict:
    """{text, language, english}: what was said, and an English version when it was said in another language
    (`context` names the equipment, so a misheard word like "Ghiya box" comes out as gearbox)."""
    r = _api().audio.transcriptions.create(model=config.MEDIA_STT_MODEL, file=(filename or "voice-note.webm", data),
                                           response_format="verbose_json")
    text = (r.text or "").strip()
    lang = (getattr(r, "language", "") or "").strip().lower()
    out = {"text": text, "language": lang or None, "english": text}
    if text and lang and lang not in ("english", "en"):
        out["english"] = _translate(text, lang, context) or text
    return out


def _translate(text: str, language: str, context: str = "") -> str | None:
    res = llm.complete_json(
        "Translate what a field operator at a biogas plant said into plain English. Keep numbers and units exactly. "
        "Speech recognition may have misheard technical words (equipment parts, oil, bearings, valves): use the "
        "context to restore them. Reply with JSON {\"english\": \"...\"}.",
        [{"role": "user", "content": (f"Context: {context}\n" if context else "") + f"({language}) {text}"}],
        {"type": "object", "additionalProperties": False, "required": ["english"],
         "properties": {"english": {"type": "string"}}}, max_tokens=600)
    return (res or {}).get("english") or None


LOOK_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["description", "answer", "confidence", "concern"],
               "properties": {"description": {"type": "string"}, "answer": {"type": "string"},
                              "confidence": {"type": "number"}, "concern": {"type": "string"}}}


def look(images: list[bytes], context: str, question: dict | None, what: str = "photo") -> dict:
    """What the photo (or video frames) shows, for troubleshooting. With a pending check, which of its options it
    shows — only when that is clearly visible."""
    opts = [o for o in (question or {}).get("options") or []]
    ask = [f"Context: {context}"]
    if question and opts:
        ask += [f"Pending check: {question.get('text')}",
                "Options: " + " | ".join(opts),
                "If the image clearly shows one option, put it in `answer` exactly as written; otherwise leave `answer` "
                "empty. confidence (0-1) is how sure you are of that answer from what is visible."]
    else:
        ask.append("No check is pending: leave `answer` empty and confidence 0.")
    system = ("You look at images that a field operator at a compressed-biogas plant attached while troubleshooting. "
              f"This is {'a video: frames side by side, left to right in time order' if what == 'video' else 'a photo'}. "
              "In `description`, say in at most two "
              "short sentences what is visible that matters for troubleshooting (equipment, readings on gauges or "
              "displays, leaks, colour, damage, smoke, wear). Describe only what you can actually see; say so when the "
              "image is unclear or doesn't show equipment. In `concern`, name any visible safety hazard, else empty. "
              "Reply with JSON only: {\"description\": str, \"answer\": str, \"confidence\": number, \"concern\": str}.")
    content = [{"type": "text", "text": "\n".join(ask)}] + [
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(_jpeg(img)).decode()}}
        for img in images]
    r = _api().chat.completions.create(model=config.MEDIA_VISION_MODEL, max_completion_tokens=500, temperature=0.1,
                                       response_format={"type": "json_object"},
                                       messages=[{"role": "system", "content": system}, {"role": "user", "content": content}])
    data = _json(r.choices[0].message.content) if r.choices else {}
    answer = (data.get("answer") or "").strip()
    match = next((o for o in opts if o.lower() == answer.lower()), None)
    try:
        conf = max(0.0, min(1.0, float(data.get("confidence") or 0)))
    except (TypeError, ValueError):
        conf = 0.0
    return {"description": (data.get("description") or "").strip(), "answer": match if match and conf >= MIN_CONFIDENCE else None,
            "hint": match if match and conf < MIN_CONFIDENCE else None, "confidence": round(conf, 2),
            "concern": (data.get("concern") or "").strip() or None}


def _json(text: str | None) -> dict:
    if not text:
        return {}
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    try:
        return json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, re.S)
        try:
            return json.loads(m.group()) if m else {}
        except ValueError:
            return {}


def read_document(data: bytes, kind: str, context: str) -> dict:
    """The text of a PDF, spreadsheet or text file, summarised for the troubleshooting."""
    text = ""
    if kind == "pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages[:8])
    elif kind == "sheet":
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        rows = []
        for ws in wb.worksheets[:3]:
            for row in ws.iter_rows(values_only=True, max_row=80):
                cells = [str(v) for v in row if v not in (None, "")]
                if cells:
                    rows.append(" | ".join(cells))
        text = "\n".join(rows)
    else:
        text = data[:20000].decode("utf-8", "replace")
    text = re.sub(r"[ \t]+", " ", text).strip()[:6000]
    if not text:
        return {"description": "No readable text in this file."}
    res = llm.complete_json(
        "A field operator at a compressed-biogas plant attached this document while troubleshooting. In at most two "
        "short sentences, say what in it matters for the problem (readings, alarms, trends, dates). JSON {\"summary\": str}.",
        [{"role": "user", "content": f"Context: {context}\n\nDocument text:\n{text}"}],
        {"type": "object", "additionalProperties": False, "required": ["summary"],
         "properties": {"summary": {"type": "string"}}}, max_tokens=500)
    return {"description": (res or {}).get("summary") or text[:300]}


# ---------------------------------------------------------------------------

def analyze(att: dict, context: str, question: dict | None) -> dict | None:
    """Read one attachment ({filename, content_type, data}). Returns {kind, summary, ...} for the chat, or None
    when the file type isn't read. `summary` is the one line shown under the file and given to the engine."""
    kind = kind_of(att["content_type"], att["filename"])
    if not kind or not enabled():
        return None
    try:
        if kind == "audio":
            t = transcribe(att["data"], att["filename"], context)
            if not t["text"]:
                return {"kind": kind, "summary": "", "error": "No speech heard in this voice note."}
            return {"kind": kind, "transcript": t["text"], "language": t["language"], "english": t["english"],
                    "summary": t["english"]}
        if kind == "image":
            v = look([att["data"]], context, question)
            return {"kind": kind, **v, "summary": v["description"]}
        if kind == "video":
            frames, sound, dur = _video_parts(att["data"])
            out = {"kind": kind, "seconds": round(dur) if dur else None}
            if frames:
                out.update(look([_tile(frames)], context, question, what="video"))
            if sound:
                try:
                    t = transcribe(sound, "video-sound.mp3", context)
                    if t["text"]:
                        out.update(transcript=t["text"], language=t["language"], english=t["english"])
                except Exception as e:  # noqa: BLE001 - the frames still count
                    log.info("video soundtrack not transcribed: %s", e)
            if not frames and not sound:
                return {"kind": kind, "summary": "", "error": "This video couldn't be read."}
            parts = [out.get("description") or ""] + ([f'Said: "{out["english"]}"'] if out.get("english") else [])
            out["summary"] = " ".join(p for p in parts if p)
            return out
        v = read_document(att["data"], kind, context)
        return {"kind": kind, **v, "summary": v["description"]}
    except Exception as e:  # noqa: BLE001 - reading is best effort; the file is kept either way
        log.warning("Couldn't read %s (%s): %s", att["filename"], kind, e)
        return {"kind": kind, "summary": "", "error": "SiteBrain couldn't read this file."}


def as_text(a: dict | None) -> str:
    """The attachment as words for the engine and the LLM transcript."""
    if not a or not a.get("summary"):
        return ""
    label = {"audio": "Voice note", "image": "Photo", "video": "Video", "pdf": "Document", "sheet": "Spreadsheet",
             "text": "Document"}.get(a["kind"], "File")
    return f"[{label}: {a['summary']}]" if a["kind"] != "audio" else a["summary"]
