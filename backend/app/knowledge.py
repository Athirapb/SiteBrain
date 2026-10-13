"""Knowledge base: RCA cases from previous problems and ingested documents (OEM manuals, SOPs, incident logs).

Batch ingestion (SRS §8 MVP): PDF / TXT / MD / CSV / XLSX are chunked and indexed with BM25 and, when available,
embeddings (app/embeddings.py). search() fuses both rankings, so a question finds passages by shared keywords
and by meaning ("shaking" ~ "vibration").

With an LLM configured, the LLM also reads each upload to tag the equipment it covers and summarise it
(profile_document), and answers knowledge-base questions from the retrieved passages, picking the relevant ones and
citing them (ask). Without an LLM, keyword tagging (detect_kinds) and plain hybrid search do the same work.
CSV incident logs with symptom/cause/resolution columns are additionally promoted to KB cases, keeping their
5-Why chain, fishbone category and preventive action when the log has them.

train() keeps the knowledge base in step with the curated knowledge brain (app/brain) and data/docs: it upserts
the RCA case library and (re-)indexes every document whose content changed. It runs at every start.
"""
import csv
import hashlib
import io
import logging
import math
import re
import threading
import time
from collections import Counter

import numpy as np

from . import config, db, embeddings, llm

log = logging.getLogger("sitebrain.knowledge")
INGEST_VERSION = b"2"  # bump when chunking or case import changes, so train() re-indexes every document


def checksum(data: bytes) -> str:
    return hashlib.sha1(INGEST_VERSION + data).hexdigest()

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set("the a an and or of to in on for with is are be by at as it this that from into was were".split())


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

def all_cases(site_code: str | None = None) -> list[dict]:
    # the full parsed report of a historic case stays out: this runs on every diagnostic turn (see case_detail)
    rows = db.q("SELECT id, site_code, kinds, keys, title, cause, fix, source, session_id, created_at, why_chain, "
                "category, prevent, equipment, doc_id, project, occurred, (report IS NOT NULL) AS historic FROM cases "
                "WHERE site_code IS NULL OR site_code=? ORDER BY historic, created_at DESC, id DESC", (site_code,))
    for r in rows:
        r["kinds"] = db.loads(r["kinds"], [])
        r["keys"] = db.loads(r["keys"], [])
        r["why_chain"] = db.loads(r.get("why_chain"), [])
        r["is_new"] = r["source"] == "Copilot session"
    return rows


def match_cases(kind: str | None, hint: str, site_code: str) -> list[dict]:
    """Past cases for this equipment type, ranked by overlap between their keys and the reported issue."""
    if not kind:
        return []
    hint = (hint or "").lower()
    out = []
    for k in all_cases(site_code):
        if kind not in k["kinds"]:
            continue
        keys = k["keys"] or []
        hit = sum(1 for key in keys if key in hint)
        sim = round(35 + 60 * hit / len(keys)) if (hint.strip() and keys) else 30
        out.append({**k, "sim": sim})
    out.sort(key=lambda x: (-x["sim"], x["id"]))
    return out


def next_case_id() -> str:
    return f"KB-{db.next_counter('case', 801):04d}"


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def _chunk(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text)
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 1 <= size:
            cur = f"{cur}\n{p}" if cur else p
            continue
        if cur:
            chunks.append(cur)
        while len(p) > size:
            chunks.append(p[:size])
            p = p[size - overlap:]
        cur = p
    if cur:
        chunks.append(cur)
    return chunks


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _docx_runs(node):
    yield node
    for child in node:
        if child.tag != _MC_FALLBACK:  # text boxes are stored twice (Choice + Fallback); read them once
            yield from _docx_runs(child)


def _docx_paragraph(p) -> str:
    out = []
    for n in _docx_runs(p):
        if n.tag == _W + "t" and n.text:
            out.append(n.text)
        elif n.tag == _W + "tab":
            out.append(" ")
        elif n.tag in (_W + "br", _W + "cr"):
            out.append("\n")
    return "".join(out).strip()


def _docx_block(el, out: list[str]) -> None:
    """Paragraphs as lines and table rows as "cell | cell | …", in document order."""
    for c in el:
        if c.tag == _W + "p":
            t = _docx_paragraph(c)
            if t:
                out.append(t)
        elif c.tag == _W + "tbl":
            for tr in c.iter(_W + "tr"):
                cells = []
                for tc in tr.findall(_W + "tc"):
                    sub: list[str] = []
                    _docx_block(tc, sub)
                    cells.append(" / ".join(sub))
                if any(cells):
                    out.append(" | ".join(cells))
        elif c.tag == _W + "sdt":
            content = c.find(_W + "sdtContent")
            _docx_block(content if content is not None else c, out)


def docx_text(data: bytes) -> str:
    import zipfile
    from xml.etree import ElementTree

    root = ElementTree.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml"))
    out: list[str] = []
    _docx_block(root.find(_W + "body"), out)
    return "\n".join(out)


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".docx"):
        return docx_text(data)
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        parts = []
        for ws in wb.worksheets:
            lines = [" | ".join(str(c).strip() for c in row if c is not None and str(c).strip())
                     for row in ws.iter_rows(values_only=True)]
            parts.append(f"# {ws.title}\n" + "\n".join(l for l in lines if l))
        return "\n\n".join(parts)
    return data.decode("utf-8", errors="replace")


CASE_KEYS = ["vibration", "sound", "noise", "oil level", "oil leakage", "oil", "leakage", "leak", "seal", "gland", "gas",
             "belt", "grease", "mesh", "material flow", "flow", "choke", "dust", "filter", "differential", "pressure",
             "breakthrough", "methane purity", "purity", "gas outlet", "dew", "temperature", "bearing", "trip", "current",
             "foam", "torque", "cake"]
KINDS = ("Agitator", "Pump", "Blower", "Compressor", "Decanter", "WAM", "Shredder", "HWG", "Chiller", "Machine",
         "Scrubber", "Filter", "Membrane")


# How each equipment type is named in manuals, SOPs and logs (used to tag what a document is about)
KIND_TERMS = {
    "Agitator": r"agitators?|mixers?", "Pump": r"pumps?", "Blower": r"blowers?", "Compressor": r"compressors?",
    "Decanter": r"decanters?|centrifuges?", "WAM": r"wam|screw press(?:es)?", "Shredder": r"shredders?",
    "HWG": r"hwgs?|hot water generators?", "Chiller": r"chillers?", "Scrubber": r"scrubbers?",
    "Filter": r"filters?|filtration", "Membrane": r"membranes?",
}
_KIND_RE = {k: re.compile(rf"\b(?:{p})\b", re.I) for k, p in KIND_TERMS.items()}


def detect_kinds(text: str, title: str = "", min_hits: int = 3) -> list[str]:
    """Equipment types a document (or passage) is mainly about. [] = general, applies to any equipment.

    A title mention counts as five body mentions; a type passing in a document about something else (a pump
    named once in a blower manual) is dropped by needing a quarter of the leading type's mentions.
    """
    counts = {k: 5 * len(rx.findall(title)) + len(rx.findall(text)) for k, rx in _KIND_RE.items()}
    top = max(counts.values())
    return sorted(k for k, n in counts.items() if n >= min_hits and n >= top / 4)


def _cases_from_csv(text: str, site_code: str | None, kind_hint: str | None, doc_id: int | None = None) -> int:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return 0
    cols = {c.lower().strip(): c for c in reader.fieldnames}

    def pick(*names):
        for n in names:  # an exact header wins over a partial match ("Equipment" vs "Equipment Type")
            if n in cols:
                return cols[n]
        for n in names:
            for lc, orig in cols.items():
                if n in lc:
                    return orig
        return None

    c_sym, c_cause = pick("symptom", "abnormal", "problem", "title"), pick("root cause", "cause", "rca")
    c_fix, c_kind = pick("resolution", "fix", "corrective"), pick("equipment type", "kind", "type")
    c_eq, c_why = pick("equipment", "equipment name", "asset"), pick("why chain", "why")
    c_cat, c_prev = pick("category", "fishbone", "6m"), pick("preventive", "prevent")
    if c_eq == c_kind:
        c_eq = None
    if not (c_sym and c_cause and c_fix):
        return 0
    from .catalog import kind_of
    n = 0
    for row in reader:
        sym, cause, fix = (row.get(c_sym) or "").strip(), (row.get(c_cause) or "").strip(), (row.get(c_fix) or "").strip()
        if not (sym and cause and fix):
            continue
        kind_raw = (row.get(c_kind) or kind_hint or "Machine") if c_kind else (kind_hint or "Machine")
        kind = kind_raw if kind_raw in KINDS else kind_of(kind_raw)
        equipment = (row.get(c_eq) or "").strip() if c_eq else ""
        text_l = f"{sym} {cause}".lower()
        why = [w.strip() for w in re.split(r"\s*>\s*", row.get(c_why) or "") if w.strip()] if c_why else []
        db.insert("cases", {"id": next_case_id(), "site_code": site_code, "kinds": [kind],
                            "keys": [k for k in CASE_KEYS if k in text_l], "title": sym + (f" on {equipment}" if equipment else ""),
                            "cause": cause, "fix": fix, "source": "Incident log import", "created_at": db.now_iso(),
                            "why_chain": why, "category": (row.get(c_cat) or "").strip() or None if c_cat else None,
                            "prevent": (row.get(c_prev) or "").strip() or None if c_prev else None,
                            "equipment": equipment or None, "doc_id": doc_id})
        n += 1
    return n


def ingest(title: str, filename: str, data: bytes, kind: str, site_code: str | None, uploaded_by: str,
           kind_hint: str | None = None, profile: bool = True, text: str | None = None,
           tags: list[str] | None = None) -> dict:
    """Chunk, embed and index a document. `profile` asks the LLM what it covers (off for the startup bulk load,
    which profiles in the background instead). `text` and `tags` skip extraction and tagging when the caller
    already has them (the incident history import)."""
    text = extract_text(filename, data) if text is None else text
    chunks = _chunk(text)
    # equipment tags: the caller's or uploader's choice, else what the LLM reads in it, else keyword detection
    prof = profile_document(title, text) if profile and tags is None and kind_hint not in KIND_TERMS else None
    if tags is not None:
        tagged_by = "import"
    elif kind_hint in KIND_TERMS:
        tags, tagged_by = [kind_hint], "uploader"
    elif prof:
        tags, tagged_by = prof["equipment_kinds"], "llm"
    else:
        tags, tagged_by = detect_kinds(text, title), "keywords"
    doc_id = db.insert("documents", {"title": title, "kind": kind, "filename": filename, "site_code": site_code,
                                     "chunk_count": len(chunks), "uploaded_by": uploaded_by, "created_at": db.now_iso(),
                                     "checksum": checksum(data), "equipment_kinds": tags, "tagged_by": tagged_by,
                                     "summary": prof["summary"] if prof else None})
    vecs = embeddings.embed([f"{title}\n{ch}" for ch in chunks])
    for i, ch in enumerate(chunks):
        row = {"doc_id": doc_id, "idx": i, "text": ch}
        if vecs is not None:
            row.update(embedding=embeddings.to_bytes(vecs[i]), embed_model=embeddings.model_name())
        db.insert("chunks", row)
    cases = _cases_from_csv(text, site_code, kind_hint, doc_id) if filename.lower().endswith(".csv") else 0
    _INDEX.clear()
    return {"id": doc_id, "title": title, "chunks": len(chunks), "cases_added": cases, "equipment_kinds": tags,
            "tagged_by": tagged_by, "summary": prof["summary"] if prof else None}


# ---------------------------------------------------------------------------
# LLM: document profiles and answers from passages
# ---------------------------------------------------------------------------

def _sample(text: str, budget: int = 3500) -> str:
    """The opening of a document plus the headings of the rest: enough to tell what it covers, in few tokens."""
    if len(text) <= budget:
        return text
    heads = [l.strip() for l in text[budget:].splitlines()
             if re.match(r"^\s*(#+\s|\d+(\.\d+)*\.?\s+[A-Z])", l) and len(l.strip()) < 120]
    return text[:budget] + "\n…\nLATER SECTIONS:\n" + "\n".join(heads[:40])


def profile_document(title: str, text: str) -> dict | None:
    """What equipment a document covers and a one-line summary, read by the LLM. None without an LLM."""
    if not llm.available() or not text.strip():
        return None
    system = (
        "You catalogue documents for the knowledge base of a compressed-biogas plant (digesters, separation, gas "
        "cleaning and upgrading). Read the document and return:\n"
        "- equipment_kinds: the equipment types whose operation, maintenance or troubleshooting it gives guidance or "
        "data for. Include a type only if a technician working on it would find this document useful; leave out "
        "types merely mentioned in passing. Return [] for site-wide documents (safety, permits, general procedures).\n"
        "  Types: Agitator (digester mixers), Pump, Blower, Compressor (LP/HP/CBG), Decanter (centrifuge), WAM (screw "
        "press separator), Shredder (feed), HWG (hot water generator / boiler), Chiller (gas dryer), Scrubber (H2S), "
        "Filter (gas filtration skid), Membrane (upgrader).\n"
        "- summary: one sentence, max 25 words, on what the document covers.")
    data = llm.complete_json(system, [{"role": "user", "content": f"TITLE: {title}\n\n{_sample(text)}"}],
                             llm.DOC_PROFILE_SCHEMA, max_tokens=400)
    if not data:
        return None
    kinds = sorted({k for k in data["equipment_kinds"] if k in KIND_TERMS})
    return {"equipment_kinds": kinds, "summary": (data.get("summary") or "").strip()[:300] or None}


def passages_block(hits: list[dict], chars: int = 550) -> str:
    """Numbered passages for an LLM prompt; the numbers are what it cites back in `sources`."""
    return "\n\n".join(f"[{i + 1}] {h['title']} ({h['kind']}; equipment: {', '.join(h['equipment_kinds']) or 'general'})"
                        f"\n{h['excerpt'][:chars]}" for i, h in enumerate(hits))


def cited(hits: list[dict], sources: list) -> list[dict]:
    """The passages an LLM cited, in its order, ignoring numbers it made up."""
    out = []
    for n in sources or []:
        if isinstance(n, int) and 1 <= n <= len(hits) and hits[n - 1] not in out:
            out.append(hits[n - 1])
    return out


def ask(question: str, site_code: str | None = None, equipment_kind: str | None = None) -> dict:
    """Answer a question from the documents: hybrid search finds candidates, the LLM keeps the relevant ones
    (re-ranking) and answers from them with citations. Without an LLM, the search results alone."""
    hits = search(f"{equipment_kind or ''} {question}", site_code, 8)
    if not hits or not llm.available():
        return {"answer": None, "found": bool(hits), "llm": False, "hits": hits}
    system = (
        "You are SiteBrain, the knowledge assistant of a compressed-biogas plant. Answer the technician's question "
        "using ONLY the numbered passages from the plant's manuals, SOPs and incident logs.\n"
        "- sources: the numbers of the passages that actually help answer it, most relevant first. Leave out passages "
        "about other equipment or that only share words with the question.\n"
        "- answer: plain language, practical, max 90 words, no emoji. Quote limits, values and steps exactly as written. "
        "Mention the document name you rely on. If the passages do not answer it, say so briefly and set found=false.\n"
        "Never invent values that are not in the passages.")
    user = (f"EQUIPMENT: {equipment_kind}\n" if equipment_kind else "") + f"QUESTION: {question}\n\nPASSAGES:\n" + \
        passages_block(hits)
    data = llm.complete_json(system, [{"role": "user", "content": user}], llm.DOC_ANSWER_SCHEMA, max_tokens=700)
    if not data:
        return {"answer": None, "found": True, "llm": False, "hits": hits}
    used = cited(hits, data["sources"])
    rest = [h for h in hits if h not in used]
    return {"answer": data["answer"].strip(), "found": bool(data["found"] and used), "llm": True,
            "hits": [{**h, "cited": True} for h in used] + [{**h, "cited": False} for h in rest]}


_profiling = threading.Lock()


def profile_pending(pause: float = 30.0) -> int:
    """Let the LLM re-tag documents tagged by keywords (startup bulk load, or indexed while no LLM was available).

    Runs in a background thread, one document every `pause` seconds so live chats keep most of the free-tier
    rate limit (Groq: tokens per minute). Stops at the first failure (rate limit, outage) and resumes on the next
    start or Train.
    """
    if not llm.available() or not _profiling.acquire(blocking=False):
        return 0
    done = 0
    try:
        docs = db.q("SELECT id, title FROM documents WHERE tagged_by IS DISTINCT FROM 'llm' "
                    "AND tagged_by IS DISTINCT FROM 'uploader' ORDER BY id")
        for d in docs:
            text = "\n\n".join(r["text"] for r in db.q("SELECT text FROM chunks WHERE doc_id=? ORDER BY idx", (d["id"],)))
            prof = profile_document(d["title"], text)
            if not prof:
                log.info("LLM document tagging paused after %s of %s documents", done, len(docs))
                break
            db.update("documents", "id", d["id"], {"equipment_kinds": prof["equipment_kinds"], "tagged_by": "llm",
                                                   "summary": prof["summary"]})
            done += 1
            _INDEX.clear()
            if done < len(docs):
                time.sleep(pause)
        if done:
            log.info("LLM tagged %s documents", done)
    finally:
        _profiling.release()
    return done


# BM25 index and embedding matrix cached in memory, rebuilt lazily after ingestion
_INDEX: dict = {}
RRF_K = 60  # reciprocal rank fusion constant: a chunk's fused score is sum(1 / (RRF_K + rank)) over both rankings


def _build_index():
    rows = db.q("SELECT c.id, c.doc_id, c.text, c.embedding, c.embed_model, d.title, d.kind, d.site_code, "
                "d.equipment_kinds, d.summary "
                "FROM chunks c JOIN documents d ON d.id=c.doc_id ORDER BY c.id")
    docs = [(r, Counter(tokenize(r["text"] + " " + r["title"]))) for r in rows]
    df = Counter()
    for _, tf in docs:
        df.update(tf.keys())
    avg = sum(sum(tf.values()) for _, tf in docs) / max(1, len(docs))
    model = embeddings.model_name()
    vec_rows = [i for i, r in enumerate(rows) if r["embedding"] is not None and r["embed_model"] == model]
    matrix = np.stack([embeddings.from_bytes(rows[i]["embedding"]) for i in vec_rows]) if vec_rows else None
    _INDEX.update({"docs": docs, "df": df, "avg": avg, "n": len(docs), "vec_rows": vec_rows, "matrix": matrix})


def _bm25(qt: list[str], allowed: list[bool]) -> list[tuple[float, int]]:
    k1, b = 1.4, 0.75
    n, df, avg = _INDEX["n"], _INDEX["df"], _INDEX["avg"]
    scored = []
    for i, (_, tf) in enumerate(_INDEX["docs"]):
        if not allowed[i]:
            continue
        dl = sum(tf.values())
        s = 0.0
        for t in qt:
            if t not in tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * dl / avg))
        if s > 0:
            scored.append((s, i))
    return sorted(scored, key=lambda x: -x[0])


def _semantic(query: str, allowed: list[bool], limit: int) -> list[tuple[float, int]]:
    if _INDEX["matrix"] is None:
        return []
    qv = embeddings.embed([query], query=True)
    if qv is None:
        return []
    sims = _INDEX["matrix"] @ qv[0]
    order = np.argsort(-sims)
    out = []
    for j in order:
        i = _INDEX["vec_rows"][j]
        if allowed[i]:
            out.append((float(sims[j]), i))
            if len(out) >= limit:
                break
    return out


def search(query: str, site_code: str | None = None, k: int = 4) -> list[dict]:
    """Hybrid search: BM25 keyword ranking and embedding similarity, merged by reciprocal rank fusion."""
    if not _INDEX:
        _build_index()
    if not _INDEX["n"] or not query.strip():
        return []
    allowed = [not (row["site_code"] and site_code and row["site_code"] != site_code) for row, _ in _INDEX["docs"]]
    qt = tokenize(query)
    lexical = _bm25(qt, allowed)[:50] if qt else []
    semantic = _semantic(query, allowed, 50)
    lex_rank = {i: r for r, (_, i) in enumerate(lexical)}
    sem = {i: (r, s) for r, (s, i) in enumerate(semantic)}
    fused: dict[int, float] = {}
    for i, r in lex_rank.items():
        fused[i] = 1 / (RRF_K + r + 1)
    for i, (r, s) in sem.items():
        if i in lex_rank or s >= config.EMBED_MIN_SIM:  # a meaning-only hit must be a close match
            fused[i] = fused.get(i, 0.0) + 1 / (RRF_K + r + 1)
    best = 2 / (RRF_K + 1)  # top of both rankings
    out, seen = [], set()
    for i in sorted(fused, key=lambda i: -fused[i]):
        row = _INDEX["docs"][i][0]
        if (row["doc_id"], row["text"][:40]) in seen:
            continue
        seen.add((row["doc_id"], row["text"][:40]))
        match = "both" if i in lex_rank and i in sem else "keyword" if i in lex_rank else "semantic"
        out.append({"doc_id": row["doc_id"], "title": row["title"], "kind": row["kind"],
                    "equipment_kinds": db.loads(row["equipment_kinds"], []), "summary": row["summary"], "score": round(100 * fused[i] / best), "match": match,
                    "similarity": round(sem[i][1], 3) if i in sem else None, "excerpt": row["text"][:600]})
        if len(out) >= k:
            break
    return out


def tag_untagged() -> int:
    """Tag documents indexed before equipment tagging existed, from their stored passages."""
    docs = db.q("SELECT id, title FROM documents WHERE equipment_kinds IS NULL")
    for d in docs:
        text = "\n".join(r["text"] for r in db.q("SELECT text FROM chunks WHERE doc_id=? ORDER BY idx", (d["id"],)))
        db.update("documents", "id", d["id"], {"equipment_kinds": detect_kinds(text, d["title"]), "tagged_by": "keywords"})
    if docs:
        _INDEX.clear()
    return len(docs)


def embed_missing() -> int:
    """Embed chunks indexed before embeddings were on, or by a different embedding model. Returns the count."""
    model = embeddings.model_name()
    if not embeddings.available():
        return 0
    rows = db.q("SELECT c.id, c.text, d.title FROM chunks c JOIN documents d ON d.id=c.doc_id "
                "WHERE c.embedding IS NULL OR c.embed_model IS DISTINCT FROM ? ORDER BY c.id", (model,))
    done = 0
    for start in range(0, len(rows), 128):
        batch = rows[start:start + 128]
        vecs = embeddings.embed([f"{r['title']}\n{r['text']}" for r in batch])
        if vecs is None:
            break
        db.executemany("UPDATE chunks SET embedding=?, embed_model=? WHERE id=?",
                       [(embeddings.to_bytes(v), model, r["id"]) for v, r in zip(vecs, batch)])
        done += len(batch)
    if done:
        _INDEX.clear()
        log.info("embedded %s passages with %s", done, model)
    return done


# ---------------------------------------------------------------------------
# Training: keep the knowledge base in step with the curated knowledge brain
# ---------------------------------------------------------------------------

def _doc_kind(name: str) -> str:
    n = name.lower()
    if n.endswith(".csv") or "incident" in n:
        return "log"
    if n.startswith("oem"):
        return "manual"
    if n.startswith("rca"):
        return "rca"
    return "sop"


def train(actor: str = "system") -> dict:
    """Upsert the RCA case library and (re-)index changed documents in data/docs. Idempotent."""
    from .brain import CASES

    for c in CASES:
        db.ex("INSERT INTO cases (id, site_code, kinds, keys, title, cause, fix, source, created_at, why_chain, category, "
              "prevent) VALUES (?,NULL,?,?,?,?,?,?,?,?,?,?) ON CONFLICT (id) DO UPDATE SET kinds=EXCLUDED.kinds, "
              "keys=EXCLUDED.keys, title=EXCLUDED.title, cause=EXCLUDED.cause, fix=EXCLUDED.fix, source=EXCLUDED.source, "
              "why_chain=EXCLUDED.why_chain, category=EXCLUDED.category, prevent=EXCLUDED.prevent",
              (c["id"], c["kinds"], c["keys"], c["title"], c["cause"], c["fix"], c.get("source") or "Maintenance records",
               db.now_iso(), c.get("why_chain") or [], c.get("category"), c.get("prevent") or None))

    # documents indexed before checksums existed are re-indexed once; their imported cases had no doc link
    legacy = db.q("SELECT id FROM documents WHERE uploaded_by='system' AND checksum IS NULL")
    if legacy:
        db.ex("DELETE FROM cases WHERE source='Incident log import' AND doc_id IS NULL")
        for d in legacy:
            db.ex("DELETE FROM documents WHERE id=?", (d["id"],))

    added = updated = 0
    docs_dir = config.DATA_DIR / "docs"
    for p in sorted(docs_dir.iterdir()) if docs_dir.exists() else []:
        if p.suffix.lower() not in (".md", ".txt", ".csv", ".pdf"):
            continue
        data = p.read_bytes()
        digest = checksum(data)
        old = db.q1("SELECT id, checksum FROM documents WHERE filename=? AND uploaded_by='system'", (p.name,))
        if old and old["checksum"] == digest:
            continue
        if old:
            db.ex("DELETE FROM cases WHERE doc_id=?", (old["id"],))
            db.ex("DELETE FROM documents WHERE id=?", (old["id"],))
        res = ingest(p.stem.replace("_", " "), p.name, data, _doc_kind(p.name), None, "system", profile=False)
        updated += 1 if old else 0
        added += 0 if old else 1
        log.info("indexed %s: %s chunks, %s cases", p.name, res["chunks"], res["cases_added"])
    tag_untagged()
    from . import incidents
    if config.INCIDENTS_DIR:  # historic PIR / RCA reports: hundreds of files, so they load in the background
        incidents.import_in_background(actor)
    embedded = embed_missing()
    threading.Thread(target=profile_pending, name="llm-doc-tagging", daemon=True).start()
    _INDEX.clear()
    from . import learning
    learned = learning.fit()
    stats = brain_stats()
    if added or updated:
        db.audit(actor, "engine", "knowledge.trained", None, {"documents_added": added, "documents_updated": updated,
                                                             "cases": stats["cases"]})
    return {**stats, "documents_added": added, "documents_updated": updated, "passages_embedded": embedded,
            "learning": learned}


def _history_progress() -> dict:
    from . import incidents
    return {k: incidents.progress[k] for k in ("running", "done", "total")}


def brain_stats() -> dict:
    from .brain import CONDITIONS, MAINTENANCE, TREES, roots

    authored = [t for t in TREES.values() if "category" in t["causes"][0]]
    docs = db.q1("SELECT COUNT(*) n, COALESCE(SUM(chunk_count),0) c FROM documents")
    return {
        "equipment_types": len(authored),
        "direct_causes": sum(len(t["causes"]) for t in authored),
        "field_checks": sum(len(t["questions"]) for t in authored),
        "root_causes": sum(len(roots(c.get("why"))) for t in authored for c in t["causes"]),
        "operating_profiles": len(CONDITIONS),
        "maintenance_entries": len(MAINTENANCE),
        "cases": db.q1("SELECT COUNT(*) n FROM cases")["n"],
        "rca_cases": db.q1("SELECT COUNT(*) n FROM cases WHERE jsonb_array_length(why_chain) > 0")["n"],
        "incident_reports": db.q1("SELECT COUNT(*) n FROM cases WHERE source='Incident log import'")["n"],
        "history_cases": db.q1("SELECT COUNT(*) n FROM cases WHERE report IS NOT NULL")["n"],
        "history_rca": db.q1("SELECT COUNT(*) n FROM cases WHERE report IS NOT NULL AND id LIKE 'RCA-%'")["n"],
        "history_projects": db.q1("SELECT COUNT(DISTINCT project) n FROM cases WHERE report IS NOT NULL")["n"],
        "history_import": _history_progress(),
        "documents": docs["n"], "passages": docs["c"],
        "passages_embedded": db.q1("SELECT COUNT(*) n FROM chunks WHERE embedding IS NOT NULL AND embed_model=?",
                                   (embeddings.model_name(),))["n"],
        "embeddings": embeddings.status(),
    }
