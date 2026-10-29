"""Auth (email and password sign-in) and analytics endpoints."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .. import analytics, db
from ..auth import ROLE_LABEL, check_password, current_user, public_user, require, site_scope

router = APIRouter(prefix="/api", tags=["auth", "analytics"])


class LoginIn(BaseModel):
    email: str
    password: str
    account_type: str = "field_operator"  # the sign-in card used: field_operator | expert | admin


@router.post("/auth/login")
def login(body: LoginIn):
    u = db.q1("SELECT * FROM users WHERE email=?", (body.email.strip().lower(),))
    if not u or not check_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect")
    if not u["active"]:
        raise HTTPException(403, "This account is switched off. Contact your administrator.")
    if body.account_type != u["role"]:
        label = ROLE_LABEL.get(u["role"], u["role"])
        raise HTTPException(403, f"This is {'an' if label[0] in 'AEIOU' else 'a'} {label} account. Use the {label} sign-in.")
    token = secrets.token_hex(24)
    db.update("users", "id", u["id"], {"token": token})
    db.audit(u["name"], u["role"], "auth.login", None, {}, u["site_code"])
    return {"token": token, "user": public_user(u)}


@router.post("/auth/logout")
def logout(user: dict = Depends(current_user)):
    db.update("users", "id", user["id"], {"token": None})
    db.audit(user["name"], user["role"], "auth.logout", None, {}, user["site_code"])
    return {"ok": True}


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
