"""User administration: the administrator adds field operators and experts with the password they will sign in
with, edits them, sets new passwords and switches accounts off. Users with issue history are switched off rather
than deleted."""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import db
from ..auth import MIN_PASSWORD, ROLE_LABEL, hash_password, public_user, require

router = APIRouter(prefix="/api/admin", tags=["admin"])

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MANAGED_ROLES = ("field_operator", "expert")
# Suggested designations for each role (free text is allowed too)
TITLES = {
    "field_operator": ["Shift In-Charge (SIC)", "Mechanical Engineer", "E&I Engineer", "Plant Manager"],
    "expert": ["Central O&M", "Design Engineer"],
}


class UserIn(BaseModel):
    name: str
    email: str
    role: str
    title: str | None = None
    site_code: str | None = None
    project_id: int | None = None
    area_code: str | None = None
    password: str


class PasswordIn(BaseModel):
    password: str


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise HTTPException(400, f"Use a password of at least {MIN_PASSWORD} characters")


class UserPatch(BaseModel):
    name: str | None = None
    role: str | None = None
    title: str | None = None
    site_code: str | None = None
    project_id: int | None = None
    area_code: str | None = None
    active: bool | None = None


def _validate(row: dict) -> None:
    if row.get("role") not in MANAGED_ROLES:
        raise HTTPException(400, "Role must be field_operator or expert")
    if not (row.get("name") or "").strip():
        raise HTTPException(400, "Enter the person's name")
    site = row.get("site_code")
    if row["role"] == "field_operator" and not site:
        raise HTTPException(400, "A field operator needs a plant")
    if site and not db.q1("SELECT code FROM sites WHERE code=?", (site,)):
        raise HTTPException(400, "Unknown plant")
    if row.get("project_id") and not db.q1("SELECT id FROM projects WHERE id=?", (row["project_id"],)):
        raise HTTPException(400, "Unknown project")
    if row.get("area_code"):
        if not site or not db.q1("SELECT id FROM areas WHERE site_code=? AND code=?", (site, row["area_code"])):
            raise HTTPException(400, "That area is not in the user's plant")


def _get(uid: int) -> dict:
    u = db.q1("SELECT * FROM users WHERE id=?", (uid,))
    if not u:
        raise HTTPException(404, "No such user")
    return u


@router.get("/options")
def options(user: dict = Depends(require("admin"))):
    """What the add-user form offers: roles, designations, plants and their areas, projects."""
    return {
        "roles": [{"id": r, "label": ROLE_LABEL[r], "titles": TITLES[r]} for r in MANAGED_ROLES],
        "sites": db.q("SELECT code, name FROM sites ORDER BY sort_order"),
        "areas": db.q("SELECT site_code, code, name FROM areas WHERE active ORDER BY site_code, sort_order"),
        "projects": db.q("SELECT id, name, code FROM projects ORDER BY id"),
    }


@router.get("/users")
def list_users(user: dict = Depends(require("admin"))):
    return [public_user(u) for u in db.q("SELECT * FROM users ORDER BY role, name")]


@router.post("/users")
def create_user(body: UserIn, user: dict = Depends(require("admin"))):
    row = body.model_dump()
    row["email"] = row["email"].strip().lower()
    row["name"] = row["name"].strip()
    if not EMAIL.match(row["email"]):
        raise HTTPException(400, "Enter a valid email address")
    if db.q1("SELECT id FROM users WHERE email=?", (row["email"],)):
        raise HTTPException(409, "A user with that email already exists")
    if row["role"] == "expert" and not row.get("site_code"):
        row["area_code"] = None
    _validate(row)
    password = row.pop("password")
    _check_password(password)
    uid = db.insert("users", {**row, "title": (row.get("title") or "").strip() or None, "active": True,
                              "password_hash": hash_password(password), "created_at": db.now_iso()})
    db.audit(user["name"], user["role"], "user.created", row["email"], {"role": row["role"], "site": row["site_code"]})
    return {"user": public_user(_get(uid))}


@router.put("/users/{uid}")
def update_user(uid: int, body: UserPatch, user: dict = Depends(require("admin"))):
    u = _get(uid)
    if u["role"] == "admin":
        raise HTTPException(400, "The administrator account is managed from the server settings")
    patch = body.model_dump(exclude_unset=True)
    row = {**u, **patch}
    if row["role"] == "expert" and not row.get("site_code"):
        patch["area_code"] = row["area_code"] = None
    _validate(row)
    if "title" in patch:
        patch["title"] = (patch["title"] or "").strip() or None
    if patch.get("active") is False:
        patch["token"] = None  # signs them out
    if patch:
        db.update("users", "id", uid, patch)
    db.audit(user["name"], user["role"], "user.updated", u["email"],
             {k: v for k, v in patch.items() if k != "token"})
    return public_user(_get(uid))


@router.put("/users/{uid}/password")
def set_password(uid: int, body: PasswordIn, user: dict = Depends(require("admin"))):
    """The administrator sets a new password; the user is signed out everywhere."""
    u = _get(uid)
    if u["role"] == "admin":
        raise HTTPException(400, "The administrator's password is set in the server's .env file")
    _check_password(body.password)
    db.update("users", "id", uid, {"password_hash": hash_password(body.password), "token": None})
    db.audit(user["name"], user["role"], "user.password_set", u["email"])
    return public_user(_get(uid))


@router.delete("/users/{uid}")
def delete_user(uid: int, user: dict = Depends(require("admin"))):
    u = _get(uid)
    if u["role"] == "admin":
        raise HTTPException(400, "The administrator account cannot be deleted")
    if db.q1("SELECT 1 FROM sessions WHERE user_id=? UNION SELECT 1 FROM escalations WHERE claimed_by=? LIMIT 1", (uid, uid)):
        raise HTTPException(409, "This user has issue history. Switch the account off instead.")
    db.ex("DELETE FROM users WHERE id=?", (uid,))
    db.audit(user["name"], user["role"], "user.deleted", u["email"])
    return {"ok": True}
