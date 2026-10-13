"""Demo authentication and role-based access control (SRS §2).

Two roles: the field operator reports and troubleshoots issues on site; the L2/L3 technical expert takes
escalations and also owns the control room (interlock release, override approval), dashboards, plant setup and
knowledge editing — so the person who requests a bypass is never the one who approves it.
Site-bound users only see their Site_ID; fleet users pick a site per request (SRS §6 tenant isolation).
"""
from fastapi import Depends, Header, HTTPException, Query

from . import db

PERMS = {
    "field_operator": {"copilot", "kb.read", "history", "esc.read"},
    "expert": {"copilot", "kb.read", "kb.write", "history", "esc.read", "esc.work", "dash", "control", "config"},
}


def public_user(u: dict) -> dict:
    return {"id": u["id"], "name": u["name"], "username": u["username"], "role": u["role"], "title": u["title"],
            "site_code": u["site_code"], "permissions": sorted(PERMS.get(u["role"], set()))}


def current_user(authorization: str = Header(default="")) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    u = db.q1("SELECT * FROM users WHERE token=?", (token,)) if token else None
    if not u:
        raise HTTPException(401, "Not signed in")
    return u


def require(perm: str):
    def dep(user: dict = Depends(current_user)) -> dict:
        perms = PERMS.get(user["role"], set())
        if perm not in perms and not (perm == "control.read" and "control" in perms):
            raise HTTPException(403, f"Role '{user['role']}' cannot access this ({perm})")
        return user
    return dep


def site_scope(user: dict = Depends(current_user), site: str | None = Query(default=None)) -> str:
    """Resolve the site for this request; site-bound users cannot reach other sites."""
    if user["site_code"]:
        if site and site != user["site_code"]:
            raise HTTPException(403, "You are not assigned to that site")
        return user["site_code"]
    if site:
        if not db.q1("SELECT code FROM sites WHERE code=?", (site,)):
            raise HTTPException(404, "Unknown site")
        return site
    return db.q1("SELECT code FROM sites ORDER BY sort_order LIMIT 1")["code"]


def check_site(user: dict, site_code: str) -> None:
    if user["site_code"] and user["site_code"] != site_code:
        raise HTTPException(403, "You are not assigned to that site")
