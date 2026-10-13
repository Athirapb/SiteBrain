"""Copilot diagnostic sessions and case history."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from .. import config, db, diagnosis, knowledge, llm, telemetry, topology
from ..auth import check_site, current_user, require, site_scope
from ..brain import tree_for
from ..catalog import KIND_ICON, report_hint

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except diagnosis.SessionError as e:
        raise HTTPException(e.status, str(e))


def stage_of(s: dict) -> dict:
    """Issue Report (0) → Fishbone (1) → 5-Why (2) → Resolution (3); expert support runs alongside."""
    phase = s["state"].get("phase") or "diagnose"
    if s["status"] in ("resolved", "closed") or s["identified"] or phase in ("fix", "verify", "done"):
        idx = 3
    elif phase == "why" or s["state"].get("rca"):
        idx = 2
    elif s["turns"] > 0 or s["state"].get("answers"):
        idx = 1
    else:
        idx = 0
    return {"index": idx, "expert": s["mode"] == "expert", "resolved": s["status"] in ("resolved", "closed")}


def session_view(sid: str, user: dict) -> dict:
    s = diagnosis.load_session(sid)
    check_site(user, s["site_code"])
    area, eq = diagnosis.load_area(s["area_id"]), diagnosis.session_eq(s)
    esc = db.q1("SELECT ticket, status, urgency, expert_name, expert_role, claimed_by, trigger_reason, compile_ms, created_at "
                "FROM escalations WHERE session_id=? ORDER BY created_at DESC", (sid,))
    cited = set(s["cited"])
    hint = report_hint(s["report"])
    kind = eq["kind"] if eq else None
    cases = [{**c, "cited": c["id"] in cited} for c in knowledge.match_cases(kind, hint, s["site_code"])[:4]]
    docs = knowledge.search(" ".join([kind or "", eq["name"] if eq else area["name"], hint] +
                                     [c["label"] for c in s["causes"][:2]]), s["site_code"], 3)
    place = eq or {"name": "", "unit": area["code"], "unit_name": area["name"]}
    st = s["state"]
    if eq and st.get("posterior") and s["engine"] == "rules":
        bones = diagnosis.fishbone(tree_for(eq["kind"]), st["posterior"], st.get("excluded", []))
    else:  # LLM-ranked causes, or no equipment yet
        bones = diagnosis.bones_from_causes(s["causes"])
    return {
        "session": {k: s[k] for k in ("id", "site_code", "area_id", "equipment_id", "status", "mode", "engine", "turns",
                                      "confidence", "causes", "cited", "identified", "symptom", "root_cause", "steps",
                                      "resolved_by", "severity", "pending_signoff", "created_at", "identified_at",
                                      "resolved_at", "report")},
        "localizing": st.get("phase") == "localize",
        "phase": st.get("phase") or "diagnose",
        "fishbone": bones,
        "survey": st.get("survey"),  # ids of the present-condition checks still waiting for answers
        "checks": len(st.get("answers", [])),
        "rca": st.get("rca"),
        "fix": st.get("fix"),
        "stage": stage_of(s),
        "messages": diagnosis.messages(sid),
        "escalation": esc,
        "cases": cases,
        "documents": docs,
        "policy": {"max_turns": config.MAX_DIAGNOSTIC_TURNS, "confidence": config.CONFIDENCE_THRESHOLD},
        "llm": llm.status(),
        "area": {k: area[k] for k in ("id", "code", "name")},
        "equipment": {k: eq[k] for k in ("id", "name", "kind", "tag", "unit", "unit_name")} if eq else None,
        "icon": KIND_ICON.get(kind, "map-marker-outline"),
        "telemetry": telemetry.snapshot(eq, diagnosis.condition(s)) if eq else None,
        "topology": topology.context_for(place),
        "interlocks": db.q("SELECT * FROM interlocks WHERE status!='released' AND (session_id=? OR equipment_id=?) "
                           "ORDER BY id DESC", (sid, eq["id"] if eq else "")),
    }


class ReportIn(BaseModel):
    project_id: int | None = None
    area_id: int | None = None
    equipment_id: str | None = None
    symptoms: list[str] = []
    severity: str = "Medium"
    description: str = ""


@router.post("")
def report_issue(body: ReportIn, user: dict = Depends(require("copilot"))):
    """Report an issue against an equipment, or an area when the equipment is not known, and start troubleshooting."""
    if body.equipment_id:
        check_site(user, _guard(diagnosis.load_eq, body.equipment_id)["site_code"])
    if body.area_id:
        check_site(user, _guard(diagnosis.load_area, body.area_id)["site_code"])
    s = _guard(diagnosis.start_session, user, body.project_id, body.area_id, body.equipment_id or None, body.symptoms,
               body.severity, body.description)
    return session_view(s["id"], user)


@router.get("/{sid}")
def get(sid: str, user: dict = Depends(current_user)):
    return _guard(session_view, sid, user)


class MsgIn(BaseModel):
    text: str
    choices: list[str] = []  # options picked together on a multi-select check


@router.post("/{sid}/messages")
def post_message(sid: str, body: MsgIn, user: dict = Depends(require("copilot"))):
    s = _guard(diagnosis.load_session, sid)
    check_site(user, s["site_code"])
    _guard(diagnosis.send, sid, body.text, user, body.choices)
    return session_view(sid, user)


async def _read_files(files: list[UploadFile]) -> list[dict]:
    if len(files) > diagnosis.MAX_ATTACHMENTS:
        raise HTTPException(400, f"Attach at most {diagnosis.MAX_ATTACHMENTS} files")
    out = []
    for f in files:
        data = await f.read(diagnosis.MAX_ATTACHMENT_BYTES + 1)  # one byte over is enough to reject it
        out.append({"filename": (f.filename or "attachment").rsplit("/", 1)[-1][:200],
                    "content_type": f.content_type or "application/octet-stream", "data": data})
    return out


@router.post("/{sid}/files")
async def share_files(sid: str, text: str = Form(""), files: list[UploadFile] = File(default=[]),
                      user: dict = Depends(require("copilot"))):
    """Photos, PDFs, spreadsheets and other files shared in the chat, with an optional message."""
    s = _guard(diagnosis.load_session, sid)
    check_site(user, s["site_code"])
    saved = _guard(diagnosis.save_files, sid, user, await _read_files(files))
    _guard(diagnosis.share_files, sid, user, text, saved)
    return session_view(sid, user)


@router.get("/{sid}/files/{aid}")
def get_file(sid: str, aid: int, user: dict = Depends(current_user)):
    s = _guard(diagnosis.load_session, sid)
    check_site(user, s["site_code"])
    a = db.q1("SELECT * FROM attachments WHERE id=? AND session_id=?", (aid, sid))
    if not a:
        raise HTTPException(404, "Unknown attachment")
    from .ops import file_response
    return file_response(a)


@router.post("/{sid}/escalate")
async def escalate(sid: str, description: str = Form(""), files: list[UploadFile] = File(default=[]),
                   user: dict = Depends(require("copilot"))):
    """The field operator hands the issue to an expert, with a description and attachments for detailed analysis."""
    s = _guard(diagnosis.load_session, sid)
    check_site(user, s["site_code"])
    attachments = await _read_files(files)
    _guard(diagnosis.escalate, sid, user, f"Escalated by {user['name']}", description, attachments)
    return session_view(sid, user)


class ResolveIn(BaseModel):
    note: str = ""  # how it was settled, when there is no confirmed root cause


@router.post("/{sid}/resolve")
def resolve(sid: str, body: ResolveIn | None = None, user: dict = Depends(require("copilot"))):
    """Mark the issue resolved and close the chat. Only the field operator who works the issue can close it."""
    if user["role"] != "field_operator":
        raise HTTPException(403, "Only the field operator can mark an issue resolved and close it")
    s = _guard(diagnosis.load_session, sid)
    check_site(user, s["site_code"])
    _guard(diagnosis.mark_resolved, sid, user, body.note if body else "")
    return session_view(sid, user)


@router.post("/{sid}/not-resolved")
def not_resolved(sid: str, user: dict = Depends(require("copilot"))):
    _guard(diagnosis.not_resolved, sid, user)
    return session_view(sid, user)


class SurveyIn(BaseModel):
    answers: dict[str, list[str]] = {}  # check id → the options seen (several when more than one applies)
    skipped: list[str] = []             # checks the operator can't do


@router.post("/{sid}/survey")
def survey(sid: str, body: SurveyIn, user: dict = Depends(require("copilot"))):
    """Answers to the present-condition checks, submitted together."""
    s = _guard(diagnosis.load_session, sid)
    check_site(user, s["site_code"])
    _guard(diagnosis.answer_survey, sid, user, body.answers, body.skipped)
    return session_view(sid, user)


class ExpertIn(BaseModel):
    text: str = ""
    root_cause: str | None = None
    steps: list[str] | None = None


@router.post("/{sid}/expert-message")
def expert_message(sid: str, body: ExpertIn, user: dict = Depends(require("esc.work"))):
    if not body.text and not body.root_cause:
        raise HTTPException(400, "Write a message or a resolution")
    _guard(diagnosis.human_expert_message, sid, user, body.text, body.root_cause,
           [x for x in (body.steps or []) if x.strip()])
    return session_view(sid, user)


@router.get("")
def history(site: str = Depends(site_scope), user: dict = Depends(require("history")),
            by: str = Query("All"), equipment_id: str | None = None, area_id: int | None = None,
            project_id: int | None = None,
            status: str | None = None, limit: int = Query(200, le=1000)):
    sql = ("SELECT s.id, s.equipment_id, s.area_id, s.status, s.mode, s.turns, s.symptom, s.root_cause, s.resolved_by, "
           "s.severity, s.created_at, s.resolved_at, COALESCE(e.name, a.name) AS eq_name, a.name AS unit_name, e.kind, "
           "s.report->>'project' AS project, s.report->>'project_code' AS project_code, "
           "(s.report->>'project_id')::int AS project_id, s.report->>'reported_by' AS reported_by, "
           "(s.equipment_id IS NULL) AS area_level FROM sessions s JOIN areas a ON a.id=s.area_id "
           "LEFT JOIN equipment e ON e.id=s.equipment_id WHERE s.site_code=?")
    params: list = [site]
    if by in ("SiteBrain", "Expert"):
        sql += " AND s.resolved_by=?"
        params.append(by)
    if equipment_id:
        sql += " AND s.equipment_id=?"
        params.append(equipment_id)
    if area_id:
        sql += " AND s.area_id=?"
        params.append(area_id)
    if project_id:
        sql += " AND (s.report->>'project_id')::int=?"
        params.append(project_id)
    if status == "open":
        sql += " AND s.status IN ('active','escalated')"
    elif status:
        sql += " AND s.status=?"
        params.append(status)
    sql += " ORDER BY s.created_at DESC LIMIT ?"
    params.append(limit)
    rows = db.q(sql, params)
    for r in rows:
        r["icon"] = KIND_ICON.get(r["kind"], "map-marker-outline")
        r["duration_min"] = diagnosis_duration(r["created_at"], r["resolved_at"])
    return rows


def diagnosis_duration(a, b):
    from ..analytics import _minutes
    m = _minutes(a, b)
    return round(m) if m is not None else None
