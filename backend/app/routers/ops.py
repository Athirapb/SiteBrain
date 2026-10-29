"""Escalation queue, control-room safety (interlocks + override approval gate), audit trail."""
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from .. import db, diagnosis, safety
from ..analytics import _minutes, _since
from ..auth import check_site, current_user, require, site_scope

router = APIRouter(prefix="/api", tags=["operations"])


def _ago(iso: str) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    m = (datetime.now(timezone.utc) - dt).total_seconds() / 60
    if m < 1:
        return "just now"
    if m < 60:
        return f"{int(m)} min ago"
    if m < 24 * 60:
        return f"{int(m // 60)} h ago"
    if m < 48 * 60:
        return "Yesterday"
    return f"{int(m // 1440)} days ago"


# ---------------------------------------------------------------------------
# Escalations
# ---------------------------------------------------------------------------

@router.get("/escalations")
def escalations(site: str = Depends(site_scope), user: dict = Depends(require("esc.read")),
                equipment_id: str | None = None, status: str | None = None, mine: bool = False,
                scope: str = Query("site"), limit: int = Query(60, le=500)):
    """The escalations of a plant, or of every plant (scope=fleet) for a fleet-wide expert. mine: the ones this
    expert answered."""
    fleet = scope == "fleet" and not user["site_code"]
    sql = ("SELECT x.ticket, x.session_id, x.equipment_id, x.urgency, x.summary, x.trigger_reason, x.expert_name, "
           "x.expert_role, x.claimed_by, x.status, x.turns, x.compile_ms, x.created_at, x.first_response_at, x.resolved_at, "
           "COALESCE(e.name, a.name) AS eq_name, a.name AS unit_name, (x.equipment_id IS NULL) AS area_level, "
           "x.site_code, st.name AS site_name, s.symptom, s.severity, s.report->>'reported_by' AS reported_by, "
           "s.report->>'project' AS project, s.root_cause, "
           # the reporter spoke last: the expert has something to answer
           "COALESCE((SELECT m.type='user' FROM messages m WHERE m.session_id=x.session_id "
           "AND (m.type='user' OR m.payload->>'expert'='true') ORDER BY m.id DESC LIMIT 1), false) AS awaiting_expert "
           "FROM escalations x JOIN areas a ON a.id=x.area_id JOIN sites st ON st.code=x.site_code "
           "LEFT JOIN sessions s ON s.id=x.session_id "
           "LEFT JOIN equipment e ON e.id=x.equipment_id WHERE " + ("TRUE" if fleet else "x.site_code=?"))
    params: list = [] if fleet else [site]
    if mine:
        sql += " AND x.claimed_by=?"
        params.append(user["id"])
    if equipment_id:
        sql += " AND x.equipment_id=?"
        params.append(equipment_id)
    if status == "open":
        sql += " AND x.status!='Resolved'"
    sql += " ORDER BY (x.status='Resolved'), x.created_at DESC LIMIT ?"
    params.append(limit)
    rows = db.q(sql, params)
    for r in rows:
        r["age"] = _ago(r["created_at"])
    month = db.q("SELECT x.*, s.created_at AS s_created FROM escalations x LEFT JOIN sessions s ON s.id=x.session_id "
                 "WHERE x.site_code=? AND x.created_at>=?", (site, _since(30)))
    sessions_30 = db.q1("SELECT COUNT(*) n FROM sessions WHERE site_code=? AND created_at>=?", (site, _since(30)))["n"]
    resp = [m for m in (_minutes(x["created_at"], x["first_response_at"]) for x in month) if m is not None]
    return {
        "items": rows,
        "stats": {
            "open": db.q1("SELECT COUNT(*) n FROM escalations WHERE site_code=? AND status!='Resolved'", (site,))["n"],
            "rate_30d_pct": round(100 * len(month) / sessions_30, 1) if sessions_30 else 0,
            "mean_response_min": round(sum(resp) / len(resp), 1) if resp else None,
            "resolved_by_experts_30d": sum(1 for x in month if x["status"] == "Resolved"),
            "mean_compile_ms": round(sum(x["compile_ms"] for x in month) / len(month)) if month else None,
        },
    }


@router.get("/escalations/{ticket}")
def escalation_detail(ticket: str, user: dict = Depends(require("esc.read"))):
    x = db.q1("SELECT * FROM escalations WHERE ticket=?", (ticket,))
    if not x:
        raise HTTPException(404, "Unknown ticket")
    check_site(user, x["site_code"])
    x["payload"] = db.loads(x["payload"], {})
    x["outbox"] = db.q("SELECT channel, recipient, subject, body, status, created_at FROM outbox WHERE ticket=? ORDER BY id",
                       (ticket,))
    x["attachments"] = db.q("SELECT id, filename, content_type, size, uploaded_by, created_at FROM attachments "
                            "WHERE ticket=? ORDER BY id", (ticket,))
    return x


@router.get("/escalations/{ticket}/attachments/{aid}")
def attachment(ticket: str, aid: int, user: dict = Depends(require("esc.read"))):
    a = db.q1("SELECT a.*, x.site_code FROM attachments a JOIN escalations x ON x.ticket=a.ticket "
              "WHERE a.id=? AND a.ticket=?", (aid, ticket))
    if not a:
        raise HTTPException(404, "Unknown attachment")
    check_site(user, a["site_code"])
    return file_response(a)


def file_response(a: dict) -> Response:
    """An uploaded attachment, served so that untrusted content cannot run in the app's origin."""
    name = a["filename"]
    plain = name.encode("ascii", "replace").decode().replace('"', "").replace("\r", "").replace("\n", "")
    ctype = a["content_type"].split(";")[0].strip().lower()
    # uploads are untrusted: only plain media is shown in the browser, anything else (HTML, SVG, ...) downloads
    inline = ctype in SAFE_INLINE or (ctype.split("/")[0] in ("image", "video", "audio") and "svg" not in ctype)
    return Response(bytes(a["data"]), media_type=ctype if inline else "application/octet-stream",
                    headers={"Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{plain}"; '
                                                    f"filename*=UTF-8''{quote(name)}",
                             "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"})


SAFE_INLINE = {"application/pdf", "text/plain"}


@router.post("/escalations/{ticket}/claim")
def claim(ticket: str, user: dict = Depends(require("esc.work"))):
    x = db.q1("SELECT * FROM escalations WHERE ticket=?", (ticket,))
    if not x:
        raise HTTPException(404, "Unknown ticket")
    if x["status"] == "Resolved":
        raise HTTPException(409, "Escalation already resolved")
    db.update("escalations", "ticket", ticket, {"claimed_by": user["id"], "expert_name": user["name"],
                                                "expert_role": user["title"], "status": "In Progress",
                                                "first_response_at": x["first_response_at"] or db.now_iso()})
    if x["session_id"]:
        diagnosis.event(x["session_id"], f"{user['name']} ({user['title'] or 'Technical Expert'}) is looking into this", "account-check-outline")
    db.audit(user["name"], user["role"], "escalation.claimed", ticket, {}, x["site_code"])
    return escalation_detail(ticket, user)


# ---------------------------------------------------------------------------
# Control room: interlocks and override approval gate
# ---------------------------------------------------------------------------

@router.get("/control/interlocks")
def interlocks(site: str = Depends(site_scope), user: dict = Depends(require("control.read")),
               status: str = Query("active")):
    sql = ("SELECT i.*, COALESCE(e.name, a.name) AS eq_name, a.name AS unit_name, e.kind FROM interlocks i "
           "JOIN areas a ON a.id=i.area_id LEFT JOIN equipment e ON e.id=i.equipment_id WHERE i.site_code=?")
    params: list = [site]
    if status == "active":
        sql += " AND i.status!='released'"
    elif status == "24h":
        sql += " AND i.created_at>=?"
        params.append(_since(1))
    sql += " ORDER BY (i.status='released'), i.created_at DESC LIMIT 300"
    rows = db.q(sql, params)
    for r in rows:
        r["age"] = _ago(r["created_at"])
        r["overridable"] = r["rule_id"] not in safety.NON_OVERRIDABLE and r["category"] == "interlock"
    return {"items": rows, "guard_filter_active": safety.bypass_guard_active(site)}


class ReleaseIn(BaseModel):
    note: str


@router.post("/control/interlocks/{iid}/release")
def release(iid: int, body: ReleaseIn, user: dict = Depends(require("control"))):
    i = db.q1("SELECT * FROM interlocks WHERE id=?", (iid,))
    if not i:
        raise HTTPException(404, "Unknown interlock")
    check_site(user, i["site_code"])
    if i["status"] == "released":
        raise HTTPException(409, "Already released")
    if not body.note.strip():
        raise HTTPException(400, "Release needs a verification note")
    if i["status"] == "engaged" and i["category"] == "interlock":
        raise HTTPException(409, "Field sign-off pending — the field operator must acknowledge the interlock first")
    db.update("interlocks", "id", iid, {"status": "released", "released_by": user["name"], "released_at": db.now_iso()})
    db.audit(user["name"], user["role"], "interlock.released", f"interlock:{iid}", {"rule": i["rule_id"], "note": body.note},
             i["site_code"])
    return db.q1("SELECT * FROM interlocks WHERE id=?", (iid,))


@router.get("/control/overrides")
def overrides(site: str = Depends(site_scope), user: dict = Depends(current_user)):
    return db.q("SELECT o.*, i.rule_id, i.action, COALESCE(e.name, a.name) AS eq_name, a.name AS unit_name FROM overrides o "
                "JOIN interlocks i ON i.id=o.interlock_id JOIN areas a ON a.id=i.area_id "
                "LEFT JOIN equipment e ON e.id=o.equipment_id "
                "WHERE o.site_code=? ORDER BY (o.status!='pending'), o.created_at DESC LIMIT 100", (site,))


class OverrideIn(BaseModel):
    interlock_id: int
    reason: str


@router.post("/control/overrides")
def request_override(body: OverrideIn, user: dict = Depends(current_user)):
    if user["role"] not in ("field_operator", "expert"):
        raise HTTPException(403, "Role cannot request overrides")
    i = db.q1("SELECT * FROM interlocks WHERE id=?", (body.interlock_id,))
    if not i:
        raise HTTPException(404, "Unknown interlock")
    check_site(user, i["site_code"])
    if i["status"] == "released":
        raise HTTPException(409, "Interlock already released")
    if not body.reason.strip():
        raise HTTPException(400, "Give a reason for the override")
    guard = safety.bypass_guard_active(i["site_code"])
    status, note = "pending", None
    if i["rule_id"] in safety.NON_OVERRIDABLE:
        status, note = "blocked", "Personnel-safety interlock — cannot be overridden; fix the cause and release after verification"
    elif i["rule_id"] in safety.BYPASS_RULES and not guard:
        status, note = "blocked", "Bypass execution invalidated: secondary guard filter is not active (FLT-01)"
    oid = db.insert("overrides", {"site_code": i["site_code"], "interlock_id": i["id"], "equipment_id": i["equipment_id"],
                                  "requested_by": user["name"], "reason": body.reason, "guard_active": 1 if guard else 0,
                                  "status": status, "decided_by": "SiteBrain" if status == "blocked" else None,
                                  "decided_at": db.now_iso() if status == "blocked" else None, "decision_note": note,
                                  "created_at": db.now_iso()})
    db.audit(user["name"], user["role"], f"override.{'blocked' if status == 'blocked' else 'requested'}", f"override:{oid}",
             {"interlock": i["id"], "rule": i["rule_id"], "reason": body.reason, "note": note}, i["site_code"])
    return db.q1("SELECT * FROM overrides WHERE id=?", (oid,))


class DecideIn(BaseModel):
    approve: bool
    note: str = ""


@router.post("/control/overrides/{oid}/decide")
def decide(oid: int, body: DecideIn, user: dict = Depends(require("control"))):
    o = db.q1("SELECT * FROM overrides WHERE id=?", (oid,))
    if not o:
        raise HTTPException(404, "Unknown override")
    check_site(user, o["site_code"])
    if o["status"] != "pending":
        raise HTTPException(409, f"Override is {o['status']}")
    i = db.q1("SELECT * FROM interlocks WHERE id=?", (o["interlock_id"],))
    if body.approve and i["rule_id"] in safety.BYPASS_RULES and not safety.bypass_guard_active(o["site_code"]):
        raise HTTPException(409, "Cannot approve: secondary guard filter is not active")
    db.update("overrides", "id", oid, {"status": "approved" if body.approve else "rejected", "decided_by": user["name"],
                                       "decided_at": db.now_iso(), "decision_note": body.note})
    if body.approve:
        db.update("interlocks", "id", i["id"], {"status": "released", "released_by": f"{user['name']} (override)",
                                                "released_at": db.now_iso()})
    db.audit(user["name"], user["role"], "override.approved" if body.approve else "override.rejected", f"override:{oid}",
             {"interlock": i["id"], "rule": i["rule_id"], "note": body.note}, o["site_code"])
    return db.q1("SELECT * FROM overrides WHERE id=?", (oid,))


@router.get("/control/outbox")
def outbox(site: str = Depends(site_scope), user: dict = Depends(require("esc.read"))):
    return db.q("SELECT o.* FROM outbox o JOIN escalations x ON x.ticket=o.ticket WHERE x.site_code=? "
                "ORDER BY o.id DESC LIMIT 50", (site,))


@router.get("/audit")
def audit(site: str = Depends(site_scope), user: dict = Depends(require("control.read")), limit: int = Query(100, le=500)):
    rows = db.q("SELECT * FROM audit_log WHERE site_code=? OR site_code IS NULL ORDER BY id DESC LIMIT ?", (site, limit))
    for r in rows:
        r["detail"] = db.loads(r["detail"], {})
    return rows
