"""Sites, equipment status, topology and telemetry."""
from fastapi import APIRouter, Depends

from .. import config, db, diagnosis, knowledge, llm, media, telemetry, topology
from ..auth import check_site, current_user, public_user, site_scope
from ..catalog import KIND_ICON, KINDS, SEVERITIES, SYMPTOMS, report_hint
from ..seed import current_shift

router = APIRouter(prefix="/api", tags=["plant"])


@router.get("/meta")
def meta(user: dict = Depends(current_user)):
    sites = db.q("SELECT * FROM sites ORDER BY sort_order")
    if user["site_code"]:
        sites = [s for s in sites if s["code"] == user["site_code"]]
    sh, start = current_shift()
    return {
        "user": public_user(user), "sites": sites, "llm": llm.status(), "media": media.enabled(),
        "current_shift": {"shift": sh, "date": start.strftime("%d %b %Y")},
        "policy": {"max_turns": config.MAX_DIAGNOSTIC_TURNS, "confidence": config.CONFIDENCE_THRESHOLD},
        "kinds": KINDS, "kind_icons": KIND_ICON, "symptoms": SYMPTOMS, "severities": SEVERITIES,
    }


def open_session(eq_id: str) -> dict | None:
    row = db.q1("SELECT id FROM sessions WHERE equipment_id=? AND status IN ('active','escalated') "
                "ORDER BY created_at DESC LIMIT 1", (eq_id,))
    return diagnosis.load_session(row["id"]) if row else None


@router.get("/equipment")
def list_equipment(site: str = Depends(site_scope), user: dict = Depends(current_user), include_inactive: bool = False):
    eqs = db.q(f"{diagnosis.EQ_SELECT} WHERE e.site_code=?"
               f"{'' if include_inactive else ' AND e.active AND a.active'} ORDER BY a.sort_order, a.name, e.name", (site,))
    open_s: dict[str, list] = {}
    for r in db.q("SELECT equipment_id, id, severity FROM sessions WHERE site_code=? AND equipment_id IS NOT NULL "
                  "AND status IN ('active','escalated') ORDER BY created_at", (site,)):
        open_s.setdefault(r["equipment_id"], []).append(r)
    locks = {r["equipment_id"]: r["n"] for r in db.q(
        "SELECT equipment_id, COUNT(*) n FROM interlocks WHERE site_code=? AND status!='released' AND category='interlock' "
        "AND equipment_id IS NOT NULL GROUP BY equipment_id", (site,))}
    out = []
    for e in eqs:
        issues = open_s.get(e["id"], [])
        status = "Critical" if any(i["severity"] == "Critical" for i in issues) else "Abnormal" if issues else "Normal"
        out.append({"id": e["id"], "area_id": e["area_id"], "unit": e["unit"], "unit_name": e["unit_name"],
                    "name": e["name"], "kind": e["kind"], "tag": e["tag"], "active": e["active"],
                    "icon": KIND_ICON.get(e["kind"], "cog-outline"), "status": status, "open_issues": len(issues),
                    "open_session_id": issues[-1]["id"] if issues else None, "interlocks": locks.get(e["id"], 0)})
    return out


@router.get("/equipment/detail")
def equipment_detail(id: str, user: dict = Depends(current_user)):
    eq = diagnosis.load_eq(id)
    check_site(user, eq["site_code"])
    s = open_session(id)
    return {
        "equipment": {k: eq[k] for k in ("id", "site_code", "area_id", "unit", "unit_name", "name", "kind", "tag", "active")},
        "icon": KIND_ICON.get(eq["kind"], "cog-outline"),
        "open_session_id": s["id"] if s else None,
        "telemetry": telemetry.snapshot(eq, diagnosis.condition(s) if s else None),
        "topology": topology.context_for(eq),
        "interlocks": db.q("SELECT * FROM interlocks WHERE equipment_id=? AND status!='released' ORDER BY id DESC", (id,)),
        "cases": knowledge.match_cases(eq["kind"], report_hint(s["report"]) if s else "", eq["site_code"])[:4],
        "history": db.q("SELECT id, status, symptom, root_cause, severity, created_at FROM sessions WHERE equipment_id=? "
                        "ORDER BY created_at DESC LIMIT 10", (id,)),
    }


@router.get("/topology")
def get_topology(site: str = Depends(site_scope), user: dict = Depends(current_user)):
    g = topology.graph()
    worst = {}
    rank = {"Normal": 0, "Abnormal": 1, "Critical": 2}
    for e in list_equipment(site, user):
        node = topology.node_of(e)
        if node and rank[e["status"]] >= rank.get(worst.get(node, "Normal"), 0):
            worst[node] = e["status"]
    for n in g["nodes"]:
        n["status"] = worst.get(n["id"], "Normal")
    return g


@router.get("/telemetry")
def get_telemetry(id: str, user: dict = Depends(current_user)):
    eq = diagnosis.load_eq(id)
    check_site(user, eq["site_code"])
    s = open_session(id)
    return telemetry.snapshot(eq, diagnosis.condition(s) if s else None)
