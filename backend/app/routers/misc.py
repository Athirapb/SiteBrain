"""Auth (demo sign-in) and analytics endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .. import analytics, db
from ..auth import current_user, public_user, require, site_scope

router = APIRouter(prefix="/api", tags=["auth", "analytics"])


@router.get("/auth/users")
def demo_users():
    return [public_user(u) for u in db.q("SELECT * FROM users ORDER BY id")]


class LoginIn(BaseModel):
    username: str


@router.post("/auth/login")
def login(body: LoginIn):
    u = db.q1("SELECT * FROM users WHERE username=?", (body.username.strip().lower(),))
    if not u:
        raise HTTPException(401, "Unknown user")
    db.audit(u["name"], u["role"], "auth.login", None, {}, u["site_code"])
    return {"token": u["token"], "user": public_user(u)}


@router.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return public_user(user)


@router.get("/projects")
def projects(user: dict = Depends(current_user)):
    return db.q("SELECT id, name, op_id, code FROM projects ORDER BY id")


@router.get("/analytics/{period}")
def get_analytics(period: str, site: str = Depends(site_scope), user: dict = Depends(require("dash")),
                  scope: str = Query("site")):
    target = None if (scope == "fleet" and not user["site_code"]) else site
    fn = {"daily": analytics.daily, "weekly": analytics.weekly, "monthly": analytics.monthly}.get(period)
    if not fn:
        raise HTTPException(404, "period must be daily, weekly or monthly")
    return {"scope": "fleet" if target is None else target, **fn(target)}
