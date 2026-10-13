import sqlite3

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import emails
from ..config import FRONTEND_URL
from ..db import get_db, now_iso
from ..mailer import send_email
from ..schemas import ForgotIn, LoginIn, PasswordIn, ProfileIn, RegisterIn, ResetIn
from ..security import (create_access_token, create_reset_token, current_user, hash_password,
                        read_reset_token, verify_password)

router = APIRouter(prefix="/api", tags=["auth"])


def public_user(u) -> dict:
    return {k: u[k] for k in ("id", "email", "full_name", "phone", "dob", "gender", "nationality",
                              "passport_no", "created_at")}


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, bg: BackgroundTasks, db: sqlite3.Connection = Depends(get_db)):
    if db.execute("SELECT 1 FROM users WHERE email=?", (str(body.email),)).fetchone():
        raise HTTPException(409, "An account with this email already exists. Try signing in.")
    cur = db.execute("INSERT INTO users(email,password_hash,full_name,phone,created_at,last_login_at) VALUES (?,?,?,?,?,?)",
                     (str(body.email).lower(), hash_password(body.password), body.full_name.strip(),
                      body.phone, now_iso(), now_iso()))
    user = db.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    subject, html = emails.welcome(user["full_name"])
    bg.add_task(send_email, user["email"], subject, html)
    return {"token": create_access_token(user["id"]), "user": public_user(user)}


@router.post("/auth/login")
def login(body: LoginIn, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute("SELECT * FROM users WHERE email=?", (str(body.email),)).fetchone()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect.")
    db.execute("UPDATE users SET last_login_at=? WHERE id=?", (now_iso(), user["id"]))
    return {"token": create_access_token(user["id"]), "user": public_user(user)}


@router.post("/auth/forgot")
def forgot(body: ForgotIn, bg: BackgroundTasks, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute("SELECT * FROM users WHERE email=?", (str(body.email),)).fetchone()
    if user:
        link = f"{FRONTEND_URL}/reset-password?token={create_reset_token(user['id'], user['password_hash'])}"
        subject, html = emails.password_reset(user["full_name"], link)
        bg.add_task(send_email, user["email"], subject, html)
    # Same answer either way so nobody can probe which emails are registered.
    return {"message": "If that email has an account, a reset link is on its way."}


@router.post("/auth/reset")
def reset(body: ResetIn, db: sqlite3.Connection = Depends(get_db)):
    user = read_reset_token(body.token, db)
    if not user:
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.")
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(body.password), user["id"]))
    return {"message": "Password updated. You can sign in now."}


@router.get("/me")
def me(user=Depends(current_user)):
    return public_user(user)


@router.put("/me")
def update_me(body: ProfileIn, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    db.execute("UPDATE users SET full_name=?,phone=?,dob=?,gender=?,nationality=?,passport_no=? WHERE id=?",
               (body.full_name.strip(), body.phone, body.dob.isoformat() if body.dob else None,
                body.gender or None, body.nationality or None,
                body.passport_no.upper() if body.passport_no else None, user["id"]))
    return public_user(db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone())


@router.post("/me/password")
def change_password(body: PasswordIn, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(400, "Current password is incorrect.")
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(body.new_password), user["id"]))
    return {"message": "Password changed."}
