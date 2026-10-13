"""Knowledge base: cases, troubleshooting library, document ingestion and search."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from .. import config, db, knowledge, learning
from ..auth import require, site_scope
from ..catalog import KIND_ICON
from .. import brain
from ..brain import tree_for

router = APIRouter(prefix="/api/kb", tags=["knowledge"])

ALLOWED = (".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx")


SOURCES = {
    "pir": lambda r: r["historic"] and r["id"].startswith("PIR-"),
    "rca": lambda r: r["historic"] and r["id"].startswith("RCA-"),
    "copilot": lambda r: r["is_new"],
    "curated": lambda r: not r["historic"] and not r["is_new"],
}


@router.get("/cases")
def cases(site: str = Depends(site_scope), user: dict = Depends(require("kb.read")),
          kind: str = Query("All"), q: str = "", source: str = Query("all"), project: str = "",
          limit: int = Query(60, ge=1, le=1000)):
    """Cases, newest first: SiteBrain's own (curated and learned) before the historic PIR / RCA reports."""
    rows = knowledge.all_cases(site)
    total = len(rows)
    projects = sorted({r["project"] for r in rows if r["project"]})
    if kind != "All":
        rows = [r for r in rows if kind in r["kinds"]]
    if source in SOURCES:
        rows = [r for r in rows if SOURCES[source](r)]
    if project:
        rows = [r for r in rows if r["project"] == project]
    words = q.strip().lower().split()
    if words:
        hay = lambda r: " ".join(str(r[k] or "") for k in ("id", "title", "cause", "fix", "prevent", "equipment",
                                                           "project", "source")).lower() + " " + " ".join(r["why_chain"]).lower()
        rows = [r for r in rows if all(w in hay(r) for w in words)]
    return {"items": rows[:limit], "matched": len(rows), "total": total, "projects": projects}


@router.get("/cases/{case_id}")
def case_detail(case_id: str, user: dict = Depends(require("kb.read"))):
    """One case with, for a historic PIR / RCA, every field read from the report and where the file is."""
    c = db.q1("SELECT c.*, d.filename AS file FROM cases c LEFT JOIN documents d ON d.id=c.doc_id WHERE c.id=?", (case_id,))
    if not c:
        raise HTTPException(404, "Unknown case")
    for k in ("kinds", "keys", "why_chain"):
        c[k] = db.loads(c[k], [])
    c["report"] = db.loads(c.get("report"), None)
    return c


@router.get("/troubleshooting")
def troubleshooting(site: str = Depends(site_scope), user: dict = Depends(require("kb.read"))):
    """The field checks and candidate causes SiteBrain works through, per equipment type in the plant."""
    out = []
    for r in db.q("SELECT kind, COUNT(*) n FROM equipment WHERE site_code=? AND active GROUP BY kind ORDER BY n DESC, kind",
                  (site,)):
        tree = tree_for(r["kind"])
        out.append({"kind": r["kind"], "icon": KIND_ICON.get(r["kind"], "cog-outline"), "count": r["n"],
                    "causes": [{"label": c["label"], "category": c.get("category", "Machine"),
                                "category_label": brain.CATEGORY_LABEL.get(c.get("category"), "Machine"),
                                "steps": c["steps"], "why": c.get("why")} for c in tree["causes"]],
                    "checks": [{"text": q["text"], "purpose": q.get("purpose"), "how": q.get("how"),
                                "options": [o["label"] for o in q["options"]]} for q in tree["questions"]],
                    "maintenance": brain.MAINTENANCE.get(r["kind"])})
    return out


@router.get("/conditions")
def conditions(site: str = Depends(site_scope), user: dict = Depends(require("kb.read"))):
    """Normal operating conditions per plant area (what good looks like, why it matters, what to do)."""
    areas = db.q("SELECT code, name FROM areas WHERE site_code=? AND active ORDER BY sort_order, name", (site,))
    out = []
    for p in brain.CONDITIONS:
        names = [a["name"] for a in areas if a["code"] in p["areas"]]
        notes = p.get("notes") or []
        out.append({"id": p["id"], "title": p["title"], "areas": names or p["areas"],
                    "notes": [notes] if isinstance(notes, str) else list(notes),
                    "params": [{"parameter": x[0], "normal": x[1], "why": x[2] if len(x) > 2 else "",
                                "action": x[3] if len(x) > 3 else ""} for x in p["params"]]})
    return out


@router.get("/brain")
def brain_stats(user: dict = Depends(require("kb.read"))):
    return knowledge.brain_stats()


@router.get("/learning")
def learning_report(kind: str | None = None, user: dict = Depends(require("kb.read"))):
    """What resolved sessions have taught the decision trees (base rates and check likelihoods)."""
    return learning.report(kind)


@router.post("/train")
def train(user: dict = Depends(require("kb.write"))):
    """Re-sync the knowledge base with the curated knowledge brain and the documents folder."""
    return knowledge.train(user["name"])


@router.get("/documents")
def documents(user: dict = Depends(require("kb.read"))):
    return db.q("SELECT * FROM documents ORDER BY id DESC")


@router.post("/documents")
async def upload(file: UploadFile = File(...), title: str = Form(""), kind: str = Form("manual"),
                 equipment_kind: str = Form(""), user: dict = Depends(require("kb.write"))):
    name = file.filename or "upload.txt"
    if not name.lower().endswith(ALLOWED):
        raise HTTPException(400, f"Supported formats: {', '.join(ALLOWED)}")
    if kind not in ("manual", "sop", "log", "checksheet"):
        raise HTTPException(400, "kind must be manual, sop, log or checksheet")
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "File larger than 25 MB")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (config.UPLOAD_DIR / name).write_bytes(data)
    try:
        res = knowledge.ingest(title.strip() or name.rsplit(".", 1)[0], name, data, kind, user["site_code"], user["name"],
                               equipment_kind or None)
    except Exception as e:  # malformed PDF / workbook
        raise HTTPException(422, f"Could not read {name}: {e}")
    db.audit(user["name"], user["role"], "knowledge.ingested", f"document:{res['id']}",
             {"file": name, "chunks": res["chunks"], "cases": res["cases_added"]}, user["site_code"])
    return res


@router.get("/search")
def search(q: str, site: str = Depends(site_scope), user: dict = Depends(require("kb.read"))):
    return knowledge.search(q, site, 6)


@router.get("/ask")
def ask(q: str, equipment_kind: str = "", site: str = Depends(site_scope), user: dict = Depends(require("kb.read"))):
    """Answer a question from the documents: the LLM picks the relevant passages and answers with citations."""
    if not q.strip():
        raise HTTPException(400, "Ask a question")
    return knowledge.ask(q.strip(), site, equipment_kind or None)


class CaseIn(BaseModel):
    kinds: list[str]
    title: str
    cause: str
    fix: str
    keys: list[str] = []


@router.post("/cases")
def add_case(body: CaseIn, user: dict = Depends(require("kb.write"))):
    if not (body.title.strip() and body.cause.strip() and body.fix.strip() and body.kinds):
        raise HTTPException(400, "Title, root cause, resolution and equipment type are required")
    cid = knowledge.next_case_id()
    db.insert("cases", {"id": cid, "site_code": None, "kinds": body.kinds, "keys": [k.lower() for k in body.keys],
                        "title": body.title, "cause": body.cause, "fix": body.fix, "source": "Expert calibration",
                        "created_at": db.now_iso()})
    db.audit(user["name"], user["role"], "knowledge.case_added", cid, {"title": body.title})
    return {"id": cid}
