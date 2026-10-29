"""Authentication and role-based access control (SRS §2).

Three roles: the field operator (SIC, engineers, plant manager) reports and troubleshoots issues on site; the
technical expert (central O&M team, design engineers) answers escalations; the administrator adds and manages
those accounts. Everyone signs in with email and password. Nobody is seeded except the administrator, whose email
and password come from .env; the administrator creates the other users and sets their passwords. Site-bound users only see their Site_ID; fleet users pick a site per request (SRS §6).
"""
import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException, Query

from . import db

ROLES = ("field_operator", "expert", "admin")
ROLE_LABEL = {"field_operator": "Field Operator", "expert": "Technical Expert", "admin": "Administrator"}

PERMS = {
    "field_operator": {"copilot", "kb.read", "history", "esc.read"},
    "expert": {"copilot", "kb.read", "kb.write", "history", "esc.read", "esc.work", "dash", "control", "config"},
    "admin": {"admin"},
}


MIN_PASSWORD = 8


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str | None) -> bool:
    try:
        algo, salt, digest = (stored or "").split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1)
    return hmac.compare_digest(got.hex(), digest)


def public_user(u: dict) -> dict:
    return {"id": u["id"], "name": u["name"], "email": u["email"], "role": u["role"],
            "role_label": ROLE_LABEL.get(u["role"], u["role"]), "title": u["title"], "site_code": u["site_code"],
            "project_id": u["project_id"], "area_code": u["area_code"], "active": u["active"],
            "created_at": u["created_at"], "has_password": bool(u.get("password_hash")),
            "permissions": sorted(PERMS.get(u["role"], set()))}


def current_user(authorization: str = Header(default="")) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    u = db.q1("SELECT * FROM users WHERE token=? AND active", (token,)) if token else None
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
