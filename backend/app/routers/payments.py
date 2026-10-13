"""Sandbox payment gateway.

No money moves and no PSP is contacted. The flow mirrors a real gateway
(create payment -> pending -> webhook/poll -> success/failed) so a real provider
such as Razorpay or Cashfree can replace `start` / `sandbox_resolve` later.
Card numbers are validated but never stored (only the last 4 digits).
"""
import secrets
import sqlite3
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import bookingsvc as svc, emails, flights as fl
from ..config import SANDBOX_PAYMENTS
from ..db import get_db, now_iso
from ..mailer import send_email
from ..schemas import UPI_RE, PaymentStartIn, SandboxResolveIn
from ..security import current_user

router = APIRouter(prefix="/api/payments", tags=["payments"])
BANKS = ["State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra Bank",
         "Canara Bank", "Bank of Baroda", "Punjab National Bank"]
FAIL_CARD = "4000000000000002"


def _luhn(num: str) -> bool:
    total, alt = 0, False
    for ch in reversed(num):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def _own_payment(db, payment_id: int, user_id: int):
    p = db.execute("SELECT p.*, b.pnr, b.user_id FROM payments p JOIN bookings b ON b.id=p.booking_id "
                   "WHERE p.id=?", (payment_id,)).fetchone()
    if not p or p["user_id"] != user_id:
        raise HTTPException(404, "Payment not found.")
    return p


def _succeed(db, payment_id: int, booking_id: int, bg: BackgroundTasks, pnr: str):
    db.execute("UPDATE payments SET status='SUCCESS',updated_at=? WHERE id=?", (now_iso(), payment_id))
    svc.confirm_booking(db, booking_id)
    b = svc.booking_dict(db, pnr)
    subject, html = emails.booking_confirmation(b)
    bg.add_task(send_email, b["contact_email"], subject, html)


def _fail(db, payment_id: int, reason: str):
    db.execute("UPDATE payments SET status='FAILED',failure_reason=?,updated_at=? WHERE id=?",
               (reason, now_iso(), payment_id))


@router.get("/banks")
def banks():
    return BANKS


@router.post("/start", status_code=201)
def start(body: PaymentStartIn, bg: BackgroundTasks, user=Depends(current_user),
          db: sqlite3.Connection = Depends(get_db)):
    fl.release_expired_holds(db)
    b = db.execute("SELECT * FROM bookings WHERE pnr=? AND user_id=?", (body.pnr.upper(), user["id"])).fetchone()
    if not b:
        raise HTTPException(404, "Booking not found.")
    if b["status"] == "CONFIRMED":
        raise HTTPException(400, "This booking is already paid.")
    if b["status"] != "PENDING_PAYMENT":
        raise HTTPException(409, "Your seat hold expired. Please select seats again.")

    upi = card_last4 = bank = None
    if body.method == "UPI":
        upi = (body.upi_id or "").strip()
        if not UPI_RE.match(upi):
            raise HTTPException(400, "Enter a valid UPI ID, for example name@okbank.")
    elif body.method == "CARD":
        num = "".join(ch for ch in (body.card_number or "") if ch.isdigit())
        if not (13 <= len(num) <= 19) or not _luhn(num):
            raise HTTPException(400, "Card number is not valid.")
        try:
            mm, yy = (body.card_expiry or "").split("/")
            exp = datetime(2000 + int(yy), int(mm), 1)
            ny = datetime.now(timezone.utc)
            if (exp.year, exp.month) < (ny.year, ny.month):
                raise ValueError
        except Exception:
            raise HTTPException(400, "Enter a card expiry in MM/YY format that has not passed.")
        if not (body.card_cvv or "").isdigit() or len(body.card_cvv) not in (3, 4):
            raise HTTPException(400, "Enter the 3 or 4 digit CVV.")
        if not (body.card_name or "").strip():
            raise HTTPException(400, "Enter the name on the card.")
        card_last4 = num[-4:]
    else:
        bank = body.bank
        if bank not in BANKS:
            raise HTTPException(400, "Choose your bank.")

    ref = ("UPI" if upi else "CRD" if card_last4 else "NB") + secrets.token_hex(6).upper()
    now = now_iso()
    cur = db.execute("INSERT INTO payments(booking_id,method,upi_id,card_last4,bank,amount,status,txn_ref,created_at,updated_at)"
                     " VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (b["id"], body.method, upi, card_last4, bank, b["total"], "PENDING", ref, now, now))
    pid = cur.lastrowid
    out = {"payment_id": pid, "txn_ref": ref, "amount": b["total"], "method": body.method, "pnr": b["pnr"]}

    if body.method == "UPI":
        # Standard UPI deep link; the payee below is a sandbox VPA, not a real account.
        out["upi_link"] = (f"upi://pay?pa=skylink@sandbox&pn=SkyLink&am={b['total']:.2f}&cu=INR"
                           f"&tn={quote('SkyLink ' + b['pnr'])}&tr={ref}")
        out["status"] = "PENDING"
        out["sandbox"] = SANDBOX_PAYMENTS
    elif num_is_fail_card(body):
        _fail(db, pid, "Card declined by the issuing bank (sandbox test card).")
        out["status"] = "FAILED"
        out["failure_reason"] = "Card declined by the issuing bank (sandbox test card)."
    else:
        _succeed(db, pid, b["id"], bg, b["pnr"])
        out["status"] = "SUCCESS"
    return out


def num_is_fail_card(body: PaymentStartIn) -> bool:
    return body.method == "CARD" and "".join(c for c in (body.card_number or "") if c.isdigit()) == FAIL_CARD


@router.get("/{payment_id}")
def status(payment_id: int, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    fl.release_expired_holds(db)
    p = _own_payment(db, payment_id, user["id"])
    return {"payment_id": p["id"], "status": p["status"], "pnr": p["pnr"], "failure_reason": p["failure_reason"]}


@router.post("/{payment_id}/sandbox-resolve")
def sandbox_resolve(payment_id: int, body: SandboxResolveIn, bg: BackgroundTasks,
                    user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    """Stands in for the customer approving/declining the request inside their UPI app."""
    if not SANDBOX_PAYMENTS:
        raise HTTPException(404, "Not found.")
    fl.release_expired_holds(db)
    p = _own_payment(db, payment_id, user["id"])
    if p["status"] != "PENDING":
        return {"payment_id": p["id"], "status": p["status"], "pnr": p["pnr"], "failure_reason": p["failure_reason"]}
    b = db.execute("SELECT * FROM bookings WHERE id=?", (p["booking_id"],)).fetchone()
    if b["status"] != "PENDING_PAYMENT":
        _fail(db, p["id"], "Seat hold expired before payment completed.")
        raise HTTPException(409, "Your seat hold expired. Please select seats again.")
    if body.outcome == "approve":
        _succeed(db, p["id"], b["id"], bg, p["pnr"])
        return {"payment_id": p["id"], "status": "SUCCESS", "pnr": p["pnr"]}
    _fail(db, p["id"], "Request declined in the UPI app.")
    return {"payment_id": p["id"], "status": "FAILED", "pnr": p["pnr"],
            "failure_reason": "Request declined in the UPI app."}
