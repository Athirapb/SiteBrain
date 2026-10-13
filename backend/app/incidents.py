"""Historic incident reports → knowledge base: PIR (Post-Incident Review) and RCA (Root Cause Analysis) documents.

The reports live in project folders under INCIDENTS_DIR (default: <repo>/data), nested to any depth, e.g.
    PIR/PIR FY25-26/GPS_JIO_03/PS_BAR_01/D-1 transfer pump.docx
    RCA/RCA FY26-27/PS_KKD_01/April 2026/RCA_04_D3 Agitator 1.pdf
Word, PDF and Excel reports are read in full. Every site writes them a little differently, so parse() reads them by
their field labels rather than by position. The families seen are:
  - PIR form: a "Field | Details" table (Project Code, Failure Title, Incident Description, What Went Wrong,
    Immediate Action Taken, ...)
  - Preliminary Information Report: "Incident Title | ...", "What went wrong | ...", "Immediate learnings | ..."
  - RCA report: "Incident Title:", "Problem Description:", "Why 1: ... ➡ ...", "Root Cause:", FMEA risk and a
    CAPA table (Corrective / Preventive / Horizontal Deployment)
  - eRCFA workbook: "Report Title:", "Immediate Cause of Failure", "Assignable Cause | Analysis" and the ticked
    root-cause categories
Each report becomes a knowledge-base case (equipment type, failure, root cause, why chain, 6M category, corrective
and preventive actions) and its full text is indexed for search and the LLM. Admin paperwork kept in the same folders
(JMS sheets, purchase orders, invoices, manpower and store records) is skipped. Importing is idempotent: unchanged
files are skipped, changed ones re-imported, deleted ones removed.

    python -m app.incidents            import / refresh now, with progress
"""
import hashlib
import logging
import re
import threading
from pathlib import Path

from . import config, db, knowledge

log = logging.getLogger("sitebrain.incidents")

IMPORTER = "history-import"  # documents.uploaded_by for imported reports
PARSER_VERSION = b"3"  # bump when parse() changes, so every report is read again
EXTENSIONS = (".docx", ".pdf", ".xlsx")
SKIP_PATH = re.compile(r"JMS Sheet|Vendor Invoice|PO Copy|Manpower|Store _|GRN Tracking|Signed copy|attendance", re.I)

# Field label (lower case, as the reports write it, matched as a prefix) → field
LABELS = [
    ("failure title", "title"), ("incident title", "title"), ("report title", "title"),
    ("problem statement", "description"), ("executive summary", "description"),
    ("project code", "project"),
    ("document number", "doc_no"), ("document no", "doc_no"), ("rca number", "doc_no"), ("ercfa report number", "doc_no"),
    ("pir ref", "pir_ref"),
    ("equipment name & tag number", "equipment"), ("equipment name", "equipment"), ("equipment:", "equipment"),
    ("equipment", "equipment"), ("unit", "unit"), ("plant / area / location", "unit"), ("location", "unit"),
    ("failure date/time", "date"), ("incident date/time", "date"), ("date of incident", "date"),
    ("date and time of incident occurrence", "date"), ("pir date", "date"), ("rca date", "date"),
    ("date & time", "date"), ("date", "date"),
    ("failure type", "failure_type"), ("incident group/type", "failure_type"), ("discipline", "failure_type"),
    ("category", "failure_type"),
    ("incident description & preliminary cause of failure", "description"), ("incident description", "description"),
    ("problem description", "description"), ("detailed description", "description"),
    ("failure breakdown occurrence details", "description"), ("problem", "description"),
    ("what went wrong", "wrong"), ("preliminary cause of failure", "wrong"), ("immediate cause of failure", "wrong"),
    ("immediate corrective action taken", "action"), ("immediate action taken", "action"),
    ("corrective action taken", "action"),
    ("primary root cause", "root"), ("root cause of failure", "root"), ("root cause", "root"),
    ("immediate learnings", "learning"), ("reviewer comments", "learning"), ("conclusion", "conclusion"),
    ("preliminary severity rating", "severity"), ("equipment damage severity", "severity"),
    ("immediate risk status", "severity"), ("risk level", "severity"),
    ("is it a repeat", "repeat"), ("impact on feeding", "impact"), ("feeding impact", "impact"),
    ("total downtime", "downtime"), ("reported by", "reported_by"), ("failure detected by", "reported_by"),
]
# headings that end a free-text block without being a field themselves
STOPS = re.compile(r"^(\d+(\.\d+)*\.?\s+[A-Z]|why[\s\-]*\d|risk |permanent corrective|corrective|preventive|"
                   r"horizontal|production loss|spares|service costing|manpower|effectiveness|pictures|photos|"
                   r"reference images|note:|rca team|participant|prepared by|reviewed by|downtime|duration|"
                   r"page \d+ of|gps renewables|root cause analysis|mixed discipline|reliability review|"
                   r"maintenance details|investigation|api 754|is it lopc|injury|equipment damage)", re.I)
BLOCK_FIELDS = {"description", "wrong", "action", "root", "learning", "conclusion"}
GENERIC_FIRST = re.compile(r"^(field\s*\|?\s*details|root cause analysis|`?root cause analysis report|gps renewables|"
                           r"pre(li)?minary information report|premin|rcfa report|# )", re.I)
EMPTY = re.compile(r"^(na|n/a|nil|none|-+|\.+|tbd|yes|no|y|n|(rca )?pending|to be (updated|submitted|confirmed))$", re.I)

# Equipment type from the equipment name / failure title, most specific first
KIND_PATTERNS = [
    (r"agitator|mixer", "Agitator"), (r"decant[oe]r|centrifuge|alfa", "Decanter"),
    (r"\bwam\b|screw press|separator", "WAM"),
    (r"shred+er|hammer ?mill|\bmill\b|\bhm\b|de-?b[ae]l+er|bale", "Shredder"),
    (r"compressor|\b[hl]p[\s_-]*(c|[a-d]|\d)\b|intercooler|cascade", "Compressor"), (r"blower|\bfan\b", "Blower"),
    (r"chiller", "Chiller"), (r"scrubber|ferrosorp|h2s", "Scrubber"), (r"membrane", "Membrane"),
    (r"filter", "Filter"), (r"\bhwg\b|hot water|boiler|heating coil|heat exchanger|burner", "HWG"),
    (r"pump|\bpc\b|\brc\b|\bcdt\b|\bpst\b|stator|rotor", "Pump"),
]
_KIND_RX = [(re.compile(p, re.I), k) for p, k in KIND_PATTERNS]

# 6M fishbone category of the root cause, by the words the reports use
CATEGORY_WORDS = {
    "Man": r"operator|not followed|negligen|human|training|awareness|skill|careless|mishandl|wrong operation|"
           r"lack of knowledge|manual(ly)? (start|operat)|unload",
    "Method": r"\bsop\b|procedure|\bpm\b|preventive maintenance|schedule|checklist|inspection (was )?not|"
              r"not (checked|inspected|monitored)|practice|planning|interlock|dol starter|monitoring",
    "Material": r"foreign|fib(re|er)|stone|sand|slurry|solids|moisture|paddy|straw|feed(stock)? (quality|material)|"
                r"rag|plastic|abrasive|grit|crust|material (defect|quality)|component defect|incorrect part|quality",
    "Measurement": r"sensor|transmitter|\blit\b|\bpt\b|\btt\b|calibrat|instrument|gauge|indicat|reading|signal|"
                   r"measurement|meter|trip setting",
    "Environment": r"rain|weather|ambient|dust|temperature|heat|humidity|water ingress|flood|lightning|"
                   r"environment|corrosi",
    "Machine": r"wear|worn|bearing|seal|gear|shaft|coupling|belt|winding|motor|fatigue|vibration|misalign|"
               r"lubricat|oil|failure|damage|design|ag(e|ing)|life",
}
_CAT_RX = {k: re.compile(rf"\b(?:{p})", re.I) for k, p in CATEGORY_WORDS.items()}


def _norm_label(s: str) -> str:
    s = re.sub(r"^\s*[\d.]+\s*[).]?\s*", "", s)  # "3.1 Production loss", "1. Incident Title"
    s = re.sub(r"\s+[-–]\s+|\s+", " ", s)  # "FAILURE BREAKDOWN - OCCURRENCE DETAILS"
    return s.strip(" :*-\t").lower()


def _field_of(label: str) -> str | None:
    lab = _norm_label(label)
    if not lab or len(lab) > 90:
        return None
    if lab.startswith("root cause analysis") or ("root cause" in lab and re.search(r"analysis|report|rcfa", lab)):
        return None
    if "root cause" in lab and len(lab) < 60:  # "Immediate (mechanical) root causes", "Contributing root causes"
        return "root"
    for alias, field in LABELS:
        a = alias.rstrip(":")
        if lab == a or lab.startswith(a + " ") or lab.startswith(a + "(") or lab.startswith(a + "/") or \
                (len(a) > 6 and lab.startswith(a)):
            return field
    return None


_PREFIX = sorted(((a.rstrip(":"), fld) for a, fld in LABELS if len(a) >= 4), key=lambda x: -len(x[0]))


def _label_prefix(line: str) -> tuple[str, str] | None:
    """'<Label> <value>' with no separator (text extracted from a PDF form)."""
    low = re.sub(r"\s+", " ", line).lower()
    for alias, field in _PREFIX:
        if low.startswith(alias + " ") and len(low) > len(alias) + 1:
            value = line.strip()[len(alias):]
            value = re.sub(r"^\s*(\([^)]*\))?\s*", "", value)  # "(Y/N)", "(Mechanical/Electrical/…)"
            return field, value
    return None


def _clean(v: str) -> str:
    v = re.sub(r"\s+", " ", v or "").strip(" |:-–•●\t")
    return "" if EMPTY.match(v) else v


def _table_whys(lines: list[str]) -> list[tuple[str, str]]:
    """5-Why tables: "1 | Why did the cable fail? | Insulation degradation due to moisture | Yes"."""
    out = []
    for l in lines:
        cells = [c.strip() for c in l.split(" | ")]
        j = next((i for i, c in enumerate(cells) if re.match(r"^(\d+\.?\s*)?why\b", c, re.I) and len(c) > 8), None)
        if j is not None and j + 1 < len(cells) and len(cells[j + 1]) > 3 and not re.match(r"^why\b", cells[j + 1], re.I):
            out.append((re.sub(r"^\d+\.?\s*", "", cells[j]).strip(" .:")[:300], cells[j + 1].strip(" .:")[:400]))
    return out


_ARROW = re.compile(r"^[\s➡→⇒️\-–>=]+")


def _line_whys(lines: list[str]) -> list[tuple[str, str]]:
    """Unnumbered or "1." numbered questions: "Why did the pump trip?" then "➡️ Because …" on the same or next line."""
    out = []
    for i, l in enumerate(lines):
        m = re.match(r"^(?:\d+\.\s*)?(?:[a-z ]{0,20}\s)?(why\b[^?]{4,}\?)\s*(.*)$", l, re.I)
        if not m or " | " in l:
            continue
        answer = _ARROW.sub("", m.group(2)).strip()
        if not answer and i + 1 < len(lines) and not re.match(r"^(\d+\.\s*)?why\b", lines[i + 1], re.I):
            answer = _ARROW.sub("", lines[i + 1]).strip()
        if answer:
            out.append((m.group(1).strip()[:300], answer.strip(" .")[:400]))
    return out


def _whys(text: str) -> list[tuple[str, str]]:
    """(question, answer) for each 'Why 1: question ➡ answer' (answers may follow on the next line)."""
    flat = re.sub(r"[ \t]+", " ", text)
    parts = re.split(r"(?im)^\s*(?:\d+\.\s*)?why[\s\-]*(\d+)\s*[:.)\-–]?\s*", flat)
    out = []
    for i in range(1, len(parts) - 1, 2):
        body = parts[i + 1]
        body = re.split(r"(?im)^\s*(root cause\b|\d+\.\s+[A-Z]|risk |permanent corrective|corrective action)", body)[0]
        body = re.sub(r"\s+", " ", body).strip()
        if len(body) < 4:
            continue
        cells = [c.strip() for c in body.split("|") if c.strip() and not re.match(r"^(yes|no|y|n)$", c.strip(), re.I)]
        if len(cells) >= 2:  # a 5-Why table row: "Why 1 | question | answer | verified"
            out.append((cells[0].strip(" .:")[:300], cells[1].strip(" .:")[:400]))
            continue
        m = re.split(r"\s*(?:➡|→|->|=>|⇒)\s*", body, maxsplit=1)
        if len(m) == 1:
            m = re.split(r"\?\s+", body, maxsplit=1)
            if len(m) == 2:
                m[0] += "?"
        if len(m) == 1:
            m = re.split(r"\s+[–-]\s+", body, maxsplit=1)
        q, a = (m[0].strip(" .:"), m[1].strip(" .:")) if len(m) == 2 else ("", m[0].strip(" .:"))
        if a or q:
            out.append((q[:300], a[:400]))
    return out


def _capa(lines: list[str]) -> dict[str, list[str]]:
    """Corrective / Preventive / Horizontal Deployment rows of the CAPA table (Word tables or flattened PDF text)."""
    out = {"corrective": [], "preventive": []}
    for l in lines:
        m = re.match(r"^\s*(corrective|preventive|horizontal deployment)\s*(?:action)?\s*[|:]?\s*(.+)$", l, re.I)
        if not m or re.match(r"^(taken|&|and|actions?\b|\()", m.group(2), re.I):
            continue  # a heading ("Corrective Action Taken (Immediate Correction)"), not an action
        cells = [c.strip() for c in m.group(2).split(" | ")]
        desc = cells[0] if cells else ""
        desc = re.sub(r"\s+\d{1,2}[-./]\d{1,2}[-./]\d{2,4}.*$", "", desc)  # trailing target date / status (PDF rows)
        desc = _clean(desc)
        if len(desc) < 6 or desc.lower() in ("description", "action", "actions"):
            continue
        out["preventive" if m.group(1).lower() != "corrective" else "corrective"].append(desc)
    return out


def _rcfa_root(lines: list[str]) -> str:
    """eRCFA workbooks tick the root-cause categories: '<category> | ✔ | <justification>'."""
    picked = []
    for l in lines:
        cells = [c.strip() for c in l.split(" | ")]
        if len(cells) > 1 and cells[1] in ("✔", "✓", "√"):
            picked.append(" — ".join(c for c in [cells[0]] + cells[2:3] if c))
    return "; ".join(picked)


def kind_from(*texts: str) -> str:
    for t in texts:
        for rx, k in _KIND_RX:
            if t and rx.search(t):
                return k
    return "Machine"


def category_from(text: str) -> str:
    scores = {k: len(rx.findall(text)) for k, rx in _CAT_RX.items()}
    weighted = {k: v * (1 if k == "Machine" else 2) for k, v in scores.items()}  # Machine words are everywhere
    best = max(weighted, key=weighted.get)
    return best if weighted[best] else "Machine"


def _site_code(v: str) -> str | None:
    """'PS_BAR_ 01', 'PS/JIN/01', 'CBG_PLANT_PS_JHA_01', 'GPS_WAR_01', 'JHA01' → the register's form, PS_XXX_NN."""
    v = re.sub(r"_+", "_", re.sub(r"[\s/\\\-]+", "_", v.upper())).strip("_,.")
    m = re.search(r"(?:^|_)G?PS_([A-Z]{1,6})_?(\d{1,2})(?:_|$)", v) or re.match(r"^([A-Z]{2,6})_?(\d{1,2})$", v)
    if not m or m.group(1) == "JIO":  # GPS_JIO_03 / _14 are client clusters, not sites
        return None
    return f"PS_{m.group(1)}_{int(m.group(2)):02d}"


# FY24-25 folders use short site names; the same reports are filed again under these site codes later
FOLDER_SITES = {"BB": "PS_BAR_01", "JJ": "PS_JHA_01", "PP": "PS_PAN_01"}


def project_from(rel: str, value: str = "") -> str | None:
    """The site the report is from: the Project Code it states, else the site folder it is filed in."""
    v = _clean(value)
    code = _site_code(v) if v else None
    if code:
        return code
    for part in reversed(Path(rel).parts[:-1]):
        if code := _site_code(part) or FOLDER_SITES.get(part.upper()):
            return code
    return None


def parse(text: str, rel: str) -> dict:
    """Fields of one PIR / RCA report, read by label. Values are '' when the report does not give them."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    pdf = rel.lower().endswith(".pdf")
    if pdf:  # every page repeats the letterhead ("GPS RENEWABLES / PVT LTD / ROOT CAUSE / ANALYSIS REPORT / PIR Ref…")
        seen: set[str] = set()
        kept = []
        for l in lines:
            if re.match(r"^(gps renewables( pvt ltd| limited)?|pvt ltd|root cause|analysis report|page \d+ of \d+)\s*$",
                        l, re.I) or (l in seen and len(l) < 120):
                continue
            seen.add(l)
            kept.append(l)
        lines = kept
    f: dict[str, str] = {}
    current = None

    def put(field, value, append=False):
        value = _clean(value)
        if not value:
            return
        if append and f.get(field):
            if value not in f[field]:
                f[field] += " " + value
        elif not f.get(field) or (field in BLOCK_FIELDS and len(f[field]) < 4):
            f[field] = value

    for line in lines:
        cells = [c.strip() for c in line.split(" | ")]
        if len(cells) > 1:
            field = _field_of(cells[0])
            if field == "downtime" or (cells[0].lower() == "duration" and len(cells) > 2):
                put("downtime", cells[-1])
                current = None
                continue
            if field == "root" and cells[1].lower().startswith("tick"):
                current = None  # eRCFA tick-box table header; _rcfa_root() reads the ticks
                continue
            if field:
                put(field, " | ".join(c for c in cells[1:] if c))
                current = field if field in BLOCK_FIELDS else None
                continue
            if current and re.match(r"^\d+\.?$", cells[0]):  # numbered rows under a heading ("1 | IR test done")
                put(current, " ".join(c for c in cells[1:] if c), append=True)
                continue
            if cells[0].lower() in ("field", "risk parameter", "action type", "sr. no", "s.no.", "user role"):
                current = None
                continue
        if pdf and (hit := _label_prefix(line)):  # PDF tables lose their borders: "Incident Title PST-2 Agitator…"
            field, value = hit
            put(field, value)
            current = field if field in BLOCK_FIELDS else None
            continue
        m = re.match(r"^([^:|]{2,70}):\s*(.*)$", line)
        if m and not re.search(r"\d", _norm_label(m.group(1))) and (field := _field_of(m.group(1))):
            put(field, m.group(2))
            current = field if field in BLOCK_FIELDS else None
            continue
        if (field := _field_of(line)) and field in BLOCK_FIELDS and len(line) < 60:  # a heading on its own line
            current = field
            continue
        if STOPS.match(line):
            current = None
            continue
        if current and " | " not in line:  # a block is prose; other tables end it
            put(current, line, append=True)
        elif " | " in line:
            current = None

    pairs = _whys(text) or _table_whys(lines) or _line_whys(lines)
    whys = [f"{q} {a}".strip() for q, a in pairs]
    capa = _capa(lines)
    # 5-Why: when the report leaves "Root Cause:" blank, the last answer is the root cause
    root = f.get("root") or _rcfa_root(lines) or next((a for q, a in reversed(pairs) if a), "")
    if not whys and re.search(r"assignable cause", text, re.I):  # eRCFA "Assignable Cause | Analysis" rows
        whys = [_clean(l.replace(" | ", ": ")) for l in lines if " | " in l and _field_of(l.split(" | ")[0]) is None
                and re.search(r"due|because|found|caused", l, re.I) and len(l) < 300][:6]

    first = lines[0] if lines else ""
    title = f.get("title") or ""
    m = re.match(r"^root cause analysis.{0,12}?\s[—–-]\s+(.{6,})$", first, re.I)
    if not title and m:  # "ROOT CAUSE ANALYSIS (RCA) — H1 SHORT SCREW KEYWAY DAMAGE"
        title = m.group(1)
    if not title:  # the title is the first line that is neither a generic heading nor a field
        title = next((l for l in lines[:3] if not GENERIC_FIRST.match(l) and " | " not in l and ":" not in l
                      and not _field_of(l) and len(l) < 120 and not re.match(r"^(prepared|reviewed|field)", l, re.I)), "")
    if not title:
        title = re.sub(r"^(copy of\s+)+", "", Path(rel).stem, flags=re.I)
    title = re.sub(r"^(PIR|RCA)\s*[–-]\s*", "", _clean(title), flags=re.I)[:160]

    is_rca = bool(whys or f.get("root") or re.search(r"root cause analysis|rcfa", first + " " + text[:400], re.I)) \
        and not re.match(r"pre(li|mi)", first, re.I)
    equipment = f.get("equipment") or ""
    if equipment and equipment.lower().startswith(("failure", "equipment")):
        equipment = ""
    desc = f.get("description") or ""
    wrong = f.get("wrong") or ""
    cause = root or wrong or desc
    if len(cause) < 25 and desc and desc not in cause:  # a terse cause ("UJ damage") reads better with what happened
        cause = f"{cause} — {desc}" if cause else desc
    corrective = capa["corrective"] or ([f["action"]] if f.get("action") else [])
    prevent = capa["preventive"] + ([f["learning"]] if f.get("learning") else [])
    return {
        "type": "RCA" if is_rca else "PIR",
        "title": title, "equipment": equipment[:160], "unit": f.get("unit", "")[:120],
        "project": project_from(rel, f.get("project", "")), "doc_no": f.get("doc_no", "")[:80],
        "pir_ref": f.get("pir_ref", "")[:80], "date": f.get("date", "")[:60],
        "failure_type": f.get("failure_type", "")[:80], "severity": f.get("severity", "")[:40],
        "repeat": f.get("repeat", "")[:20], "impact": f.get("impact", "")[:20], "downtime": f.get("downtime", "")[:40],
        "description": desc[:2000], "what_went_wrong": wrong[:1500], "immediate_action": f.get("action", "")[:1500],
        "root_cause": root[:1500], "why_chain": whys[:8], "corrective": corrective[:8], "preventive": prevent[:8],
        "conclusion": f.get("conclusion", "")[:1500],
        "kind": kind_from(equipment, title, f.get("unit", ""), wrong, desc),
        "category": category_from(" ".join([root, " ".join(whys), wrong])),
        "cause": cause[:1500],
    }


def is_incident(p: dict) -> bool:
    """A report SiteBrain can learn from: it names the failure and says what caused it or what happened."""
    return bool(p["title"]) and len(p["cause"]) >= 6


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

_lock = threading.Lock()
progress: dict = {"running": False, "done": 0, "total": 0, "cases": 0, "documents": 0, "skipped": 0, "errors": 0}


def files(root: Path | None = None) -> list[Path]:
    root = root or config.INCIDENTS_DIR
    if not root or not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS
                  and not SKIP_PATH.search(str(p.relative_to(root))) and not p.name.startswith("~$"))


def case_id(p: dict, rel: str) -> str:
    return f"{p['type']}-{hashlib.sha1(rel.encode()).hexdigest()[:6].upper()}"


def _case_row(p: dict, rel: str, doc_id: int) -> dict:
    text_l = " ".join([p["title"], p["description"], p["what_went_wrong"], p["cause"]]).lower()
    where = " · ".join(x for x in [p["project"], p["date"]] if x)
    title = p["title"] + (f" on {p['equipment']}" if p["equipment"] and p["equipment"].lower() not in p["title"].lower()
                          else "")
    return {"id": case_id(p, rel), "site_code": None, "kinds": [p["kind"]],
            "keys": [k for k in knowledge.CASE_KEYS if k in text_l], "title": title[:240],
            "cause": p["cause"], "fix": "; ".join(p["corrective"]) or "Not recorded in the report",
            "source": f"{p['type']} report" + (f" · {where}" if where else ""), "session_id": None,
            "created_at": db.now_iso(), "why_chain": p["why_chain"], "category": p["category"],
            "prevent": "; ".join(p["preventive"]) or None, "equipment": p["equipment"] or None, "doc_id": doc_id,
            "project": p["project"], "occurred": p["date"] or None, "report": p}


_ADVISORY_KEY = 71_640_201  # pg advisory lock: one import at a time across every server worker and the CLI


def import_all(root: Path | None = None, actor: str = "system") -> dict:
    """Import or refresh every report under root. Safe to run repeatedly, from a background thread and from
    several processes at once (the others return busy)."""
    if not _lock.acquire(blocking=False):
        return {**progress, "busy": True}
    held = db.pool().getconn()
    try:
        if not held.execute("SELECT pg_try_advisory_lock(%s) AS ok", (_ADVISORY_KEY,)).fetchone()["ok"]:
            return {**progress, "busy": True}
        try:
            return _import(root, actor)
        finally:
            held.execute("SELECT pg_advisory_unlock(%s)", (_ADVISORY_KEY,))
    finally:
        db.pool().putconn(held)
        _lock.release()


def _import(root: Path | None, actor: str) -> dict:
    try:
        root = root or config.INCIDENTS_DIR
        if not root:
            return {"disabled": True}
        paths = files(root)
        progress.update(running=True, done=0, total=len(paths), cases=0, documents=0, skipped=0, errors=0)
        known = {d["filename"]: d for d in db.q("SELECT id, filename, checksum FROM documents WHERE uploaded_by=?",
                                                 (IMPORTER,))}
        seen_paths, seen_sums, seen_incidents = set(), set(), set()
        added = updated = 0
        for path in paths:
            rel = str(path.relative_to(root))
            seen_paths.add(rel)
            progress["done"] += 1
            try:
                data = path.read_bytes()
                digest = knowledge.checksum(PARSER_VERSION + data)
                old = known.get(rel)
                if old and old["checksum"] == digest:
                    seen_sums.add(digest)
                    progress["skipped"] += 1
                    continue
                if old:
                    _remove(old["id"])
                if digest in seen_sums or db.q1("SELECT id FROM documents WHERE checksum=? AND uploaded_by=?",
                                                (digest, IMPORTER)):
                    progress["skipped"] += 1  # the same file filed in two folders ("Copy of …")
                    continue
                seen_sums.add(digest)
                text = knowledge.extract_text(path.name, data)
                if len(text.strip()) < 40:
                    progress["skipped"] += 1  # scanned image or empty file: nothing to read
                    continue
                p = parse(text, rel)
                incident = is_incident(p)
                key = (p["title"].lower(), p["date"], p["project"], p["type"])
                if incident and key in seen_incidents:
                    incident = False  # same report saved under two names: index the text once more, no second case
                seen_incidents.add(key)
                doc_kind = p["type"].lower() if incident else "reference"
                title = f"{p['type']} · {p['project'] or 'Fleet'} · {p['title']}" if incident else path.stem
                res = knowledge.ingest(title[:200], rel, data, doc_kind, None, IMPORTER, profile=False, text=text,
                                       tags=[p["kind"]] if incident and p["kind"] != "Machine" else [])
                progress["documents"] += 1
                if incident:
                    row = _case_row(p, rel, res["id"])
                    db.ex("DELETE FROM cases WHERE id=?", (row["id"],))
                    db.insert("cases", row)
                    progress["cases"] += 1
                updated += 1 if old else 0
                added += 0 if old else 1
            except Exception as e:  # one unreadable report must not stop the rest
                progress["errors"] += 1
                log.warning("could not import %s: %s", rel, e)
        removed = 0
        for rel, d in known.items():
            if rel not in seen_paths:
                _remove(d["id"])
                removed += 1
        embedded = knowledge.embed_missing() if added or updated else 0
        knowledge._INDEX.clear()
        stats = {"files": len(paths), "added": added, "updated": updated, "removed": removed,
                 "unchanged": progress["skipped"], "errors": progress["errors"], "passages_embedded": embedded,
                 "cases": db.q1("SELECT COUNT(*) n FROM cases WHERE doc_id IN (SELECT id FROM documents "
                                "WHERE uploaded_by=?)", (IMPORTER,))["n"]}
        if added or updated or removed:
            db.audit(actor, "engine", "incidents.imported", None, stats)
        log.info("incident history: %s", stats)
        return stats
    finally:
        progress["running"] = False


def _remove(doc_id: int) -> None:
    db.ex("DELETE FROM cases WHERE doc_id=?", (doc_id,))
    db.ex("DELETE FROM documents WHERE id=?", (doc_id,))


def import_in_background(actor: str = "system") -> None:
    threading.Thread(target=import_all, kwargs={"actor": actor}, name="incident-import", daemon=True).start()


if __name__ == "__main__":
    import sys
    import time

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    db.init_schema()
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    t = threading.Thread(target=lambda: print(import_all(root)))
    t.start()
    while t.is_alive():
        time.sleep(3)
        if progress["total"]:
            print(f"  {progress['done']}/{progress['total']} files · {progress['cases']} cases · "
                  f"{progress['skipped']} unchanged/duplicate · {progress['errors']} errors", flush=True)
    t.join()
