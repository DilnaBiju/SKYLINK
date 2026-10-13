import sqlite3

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response

from .. import bookingsvc as svc, emails, flights as fl
from ..db import get_db
from ..mailer import send_email
from ..schemas import BookingIn, PromoIn
from ..security import current_user
from ..ticketpdf import build_ticket_pdf

router = APIRouter(prefix="/api", tags=["bookings"])


@router.post("/promos/validate")
def validate_promo(body: PromoIn, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    f = db.execute("SELECT * FROM flights WHERE id=?", (body.flight_id,)).fetchone()
    if not f:
        raise HTTPException(404, "Flight not found.")
    fd = fl.flight_dict(db, f, with_seats=False)
    extra = 0.0
    for s in body.seat_nos:
        r = db.execute("SELECT price_add FROM flight_seats WHERE flight_id=? AND seat_no=?", (f["id"], s.upper())).fetchone()
        extra += r["price_add"] if r else 0
    subtotal = f["fare"] * max(1, len(body.seat_nos)) + extra
    discount, err = svc.promo_discount(db, body.code, subtotal, fd["international"], user["id"])
    if err:
        raise HTTPException(400, err)
    return {"code": body.code.upper(), "discount": discount}


@router.post("/bookings", status_code=201)
def create(body: BookingIn, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    return svc.create_booking(db, user, body)


@router.get("/bookings")
def mine(user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    fl.release_expired_holds(db)
    pnrs = [r["pnr"] for r in db.execute(
        "SELECT pnr FROM bookings WHERE user_id=? AND status!='EXPIRED' ORDER BY created_at DESC", (user["id"],))]
    return [svc.booking_dict(db, p) for p in pnrs]


@router.get("/bookings/{pnr}")
def one(pnr: str, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    return svc.booking_dict(db, pnr, user["id"])


@router.post("/bookings/{pnr}/cancel")
def cancel(pnr: str, bg: BackgroundTasks, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    was = svc.booking_dict(db, pnr, user["id"])["status"]
    svc.cancel_booking(db, user["id"], pnr)
    b = svc.booking_dict(db, pnr, user["id"])
    if was == "CONFIRMED":
        subject, html = emails.cancellation(b)
        bg.add_task(send_email, b["contact_email"], subject, html)
    return b


@router.get("/bookings/{pnr}/ticket.pdf")
def ticket_pdf(pnr: str, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    b = svc.booking_dict(db, pnr, user["id"])
    if b["status"] != "CONFIRMED":
        raise HTTPException(400, "A ticket is only available for confirmed bookings.")
    return Response(build_ticket_pdf(b), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="SkyLink-{b["pnr"]}.pdf"'})
