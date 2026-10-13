"""Plant Setup: configure the areas of a site and the equipment in each area.

Issues are reported against these areas and equipment. Records that already have issue history cannot be
deleted (sessions, interlocks and escalations point at them); mark them inactive instead.
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .. import db
from ..auth import check_site, current_user, require, site_scope
from ..catalog import KIND_ICON, KINDS

router = APIRouter(prefix="/api", tags=["setup"])

_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,11}$")


def _area(area_id: int, user: dict) -> dict:
    a = db.q1("SELECT * FROM areas WHERE id=?", (area_id,))
    if not a:
        raise HTTPException(404, "Unknown area")
    check_site(user, a["site_code"])
    return a


def _equipment(eq_id: str, user: dict) -> dict:
    e = db.q1("SELECT * FROM equipment WHERE id=?", (eq_id,))
    if not e:
        raise HTTPException(404, "Unknown equipment")
    check_site(user, e["site_code"])
    return e


# ---------------------------------------------------------------------------
# Areas
# ---------------------------------------------------------------------------

@router.get("/areas")
def list_areas(site: str = Depends(site_scope), user: dict = Depends(current_user), include_inactive: bool = False):
    return db.q(
        "SELECT a.*, "
        "(SELECT COUNT(*) FROM equipment e WHERE e.area_id=a.id AND e.active) AS equipment_count, "
        "(SELECT COUNT(*) FROM equipment e WHERE e.area_id=a.id) AS equipment_total, "
        "(SELECT COUNT(*) FROM sessions s WHERE s.area_id=a.id AND s.status IN ('active','escalated')) AS open_issues "
        f"FROM areas a WHERE a.site_code=?{'' if include_inactive else ' AND a.active'} ORDER BY a.sort_order, a.name",
        (site,))


class AreaIn(BaseModel):
    code: str
    name: str
    description: str = ""
    sort_order: int | None = None
    active: bool = True


def _clean_area(body: AreaIn, site: str, area_id: int | None = None) -> dict:
    code, name = body.code.strip().upper(), body.name.strip()
    if not _CODE.match(code):
        raise HTTPException(400, "Area code: 1–12 letters, digits, '-' or '_' (e.g. BUU, D1)")
    if not name:
        raise HTTPException(400, "Area name is required")
    clash = db.q1("SELECT id FROM areas WHERE site_code=? AND (UPPER(code)=? OR LOWER(name)=?) AND id!=?",
                  (site, code, name.lower(), area_id or 0))
    if clash:
        raise HTTPException(409, "Another area at this site already uses that code or name")
    return {"code": code, "name": name, "description": body.description.strip() or None, "active": body.active}


@router.post("/areas")
def create_area(body: AreaIn, site: str = Depends(site_scope), user: dict = Depends(require("config"))):
    row = _clean_area(body, site)
    nxt = db.q1("SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM areas WHERE site_code=?", (site,))["n"]
    row.update(site_code=site, sort_order=body.sort_order if body.sort_order is not None else nxt)
    row["id"] = db.insert("areas", row)
    db.audit(user["name"], user["role"], "setup.area_created", f"area:{row['id']}", {"code": row["code"], "name": row["name"]}, site)
    return row


@router.put("/areas/{area_id}")
def update_area(area_id: int, body: AreaIn, user: dict = Depends(require("config"))):
    a = _area(area_id, user)
    row = _clean_area(body, a["site_code"], area_id)
    if body.sort_order is not None:
        row["sort_order"] = body.sort_order
    db.update("areas", "id", area_id, row)
    db.audit(user["name"], user["role"], "setup.area_updated", f"area:{area_id}",
             {"before": {k: a[k] for k in row}, "after": row}, a["site_code"])
    return db.q1("SELECT * FROM areas WHERE id=?", (area_id,))


@router.delete("/areas/{area_id}")
def delete_area(area_id: int, user: dict = Depends(require("config"))):
    a = _area(area_id, user)
    if db.q1("SELECT id FROM equipment WHERE area_id=? LIMIT 1", (area_id,)):
        raise HTTPException(409, "Move or delete the equipment in this area first")
    if db.q1("SELECT id FROM sessions WHERE area_id=? LIMIT 1", (area_id,)):
        raise HTTPException(409, "This area has issue history — mark it inactive instead")
    db.ex("DELETE FROM areas WHERE id=?", (area_id,))
    db.audit(user["name"], user["role"], "setup.area_deleted", f"area:{area_id}", {"code": a["code"], "name": a["name"]},
             a["site_code"])
    return {"ok": True}


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

class EquipmentIn(BaseModel):
    area_id: int
    name: str
    kind: str
    tag: str | None = None
    active: bool = True


def _clean_equipment(body: EquipmentIn, user: dict, eq_id: str | None = None) -> tuple[dict, dict]:
    area = _area(body.area_id, user)
    name = re.sub(r"\s+", " ", body.name).strip()
    if not name:
        raise HTTPException(400, "Equipment name is required")
    if body.kind not in KINDS:
        raise HTTPException(400, f"Type must be one of {', '.join(KINDS)}")
    if db.q1("SELECT id FROM equipment WHERE site_code=? AND LOWER(name)=? AND id!=?",
             (area["site_code"], name.lower(), eq_id or "")):
        raise HTTPException(409, f"An equipment named {name} already exists at this site")
    return area, {"area_id": area["id"], "name": name, "kind": body.kind, "tag": (body.tag or "").strip() or None,
                  "active": body.active}


@router.post("/equipment")
def create_equipment(body: EquipmentIn, user: dict = Depends(require("config"))):
    area, row = _clean_equipment(body, user)
    base = f"{area['site_code']}|{area['code']}|{row['name']}"
    eq_id, n = base, 1
    while db.q1("SELECT id FROM equipment WHERE id=?", (eq_id,)):
        n += 1
        eq_id = f"{base}-{n}"
    row.update(id=eq_id, site_code=area["site_code"], created_at=db.now_iso())
    db.insert("equipment", row)
    db.audit(user["name"], user["role"], "setup.equipment_created", eq_id,
             {"area": area["code"], "name": row["name"], "kind": row["kind"]}, area["site_code"])
    return {**row, "icon": KIND_ICON.get(row["kind"], "cog-outline")}


@router.put("/equipment")
def update_equipment(body: EquipmentIn, id: str = Query(...), user: dict = Depends(require("config"))):
    e = _equipment(id, user)
    area, row = _clean_equipment(body, user, id)
    if area["site_code"] != e["site_code"]:
        raise HTTPException(400, "Equipment can only move between areas of the same site")
    db.update("equipment", "id", id, row)
    db.audit(user["name"], user["role"], "setup.equipment_updated", id,
             {"before": {k: e[k] for k in row}, "after": row}, e["site_code"])
    return {**db.q1("SELECT * FROM equipment WHERE id=?", (id,)), "icon": KIND_ICON.get(row["kind"], "cog-outline")}


@router.delete("/equipment")
def delete_equipment(id: str = Query(...), user: dict = Depends(require("config"))):
    e = _equipment(id, user)
    for table in ("sessions", "interlocks", "escalations"):
        if db.q1(f"SELECT 1 AS x FROM {table} WHERE equipment_id=? LIMIT 1", (id,)):
            raise HTTPException(409, f"{e['name']} has issue history — mark it inactive instead")
    db.ex("DELETE FROM equipment WHERE id=?", (id,))
    db.audit(user["name"], user["role"], "setup.equipment_deleted", id, {"name": e["name"]}, e["site_code"])
    return {"ok": True}
