import random
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from . import flights as fl
from .config import SEAT_HOLD_MINUTES
from .db import now_iso, transaction

PNR_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_pnr(db) -> str:
    while True:
        pnr = "".join(secrets.choice(PNR_CHARS) for _ in range(6))
        if not db.execute("SELECT 1 FROM bookings WHERE pnr=?", (pnr,)).fetchone():
            return pnr


def tax_rate(international: bool) -> float:
    return 0.12 if international else 0.08


def promo_discount(db, code: str | None, subtotal: float, international: bool, user_id: int):
    """Returns (discount, error). code None -> (0, None)."""
    if not code:
        return 0.0, None
    p = db.execute("SELECT * FROM promos WHERE code=? AND active=1", (code.strip().upper(),)).fetchone()
    if not p:
        return 0.0, "That promo code is not valid."
    if subtotal < p["min_amount"]:
        return 0.0, f"This code needs a minimum booking of ₹{int(p['min_amount']):,}."
    if p["international_only"] and not international:
        return 0.0, "This code works on international flights only."
    if p["first_booking_only"] and db.execute(
            "SELECT 1 FROM bookings WHERE user_id=? AND status='CONFIRMED' LIMIT 1", (user_id,)).fetchone():
        return 0.0, "This code is for your first booking only."
    d = subtotal * p["value"] / 100 if p["kind"] == "PERCENT" else p["value"]
    if p["max_discount"]:
        d = min(d, p["max_discount"])
    return float(round(min(d, subtotal))), None


def create_booking(db: sqlite3.Connection, user, payload) -> dict:
    flight = db.execute("SELECT * FROM flights WHERE id=? AND status='SCHEDULED'", (payload.flight_id,)).fetchone()
    if not flight:
        raise HTTPException(404, "This flight is no longer available.")
    origin = fl.get_airport(db, flight["origin"])
    if fl.depart_utc(flight["dep_local"], origin["tz_minutes"]) < datetime.now(timezone.utc) + timedelta(hours=2):
        raise HTTPException(400, "Booking is closed for this flight.")
    fd = fl.flight_dict(db, flight, with_seats=False)
    seats = [p.seat_no.upper() for p in payload.passengers]
    if len(set(seats)) != len(seats):
        raise HTTPException(400, "Each passenger needs a different seat.")
    if fd["international"]:
        for p in payload.passengers:
            if not p.passport_no or not re.fullmatch(r"[A-Za-z0-9]{6,9}", p.passport_no):
                raise HTTPException(400, f"Passport number is required for {p.full_name} (6–9 letters/digits).")

    with transaction(db):
        fl.release_expired_holds(db)
        seat_rows = {}
        for s in seats:
            r = db.execute("SELECT * FROM flight_seats WHERE flight_id=? AND seat_no=?", (flight["id"], s)).fetchone()
            if not r:
                raise HTTPException(400, f"Seat {s} does not exist on this flight.")
            if r["status"] != "AVAILABLE":
                raise HTTPException(409, f"Seat {s} was just taken. Please choose another seat.")
            seat_rows[s] = r
        n = len(seats)
        base = flight["fare"] * n
        seat_amount = sum(r["price_add"] for r in seat_rows.values())
        subtotal = base + seat_amount
        discount, err = promo_discount(db, payload.promo_code, subtotal, fd["international"], user["id"])
        if err:
            raise HTTPException(400, err)
        taxes = round((subtotal - discount) * tax_rate(fd["international"]))
        total = subtotal - discount + taxes
        pnr, now = new_pnr(db), now_iso()
        hold_until = (datetime.now(timezone.utc) + timedelta(minutes=SEAT_HOLD_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
        cur = db.execute(
            "INSERT INTO bookings(pnr,user_id,flight_id,status,pax_count,base_amount,seat_amount,taxes,discount,total,"
            "promo_code,contact_email,contact_phone,hold_until,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pnr, user["id"], flight["id"], "PENDING_PAYMENT", n, base, seat_amount, taxes, discount, total,
             payload.promo_code.strip().upper() if payload.promo_code and discount else None,
             str(payload.contact_email), payload.contact_phone, hold_until, now))
        bid = cur.lastrowid
        for p in payload.passengers:
            s = p.seat_no.upper()
            db.execute("INSERT INTO passengers(booking_id,full_name,age,gender,passport_no,seat_no,seat_price,fare)"
                       " VALUES (?,?,?,?,?,?,?,?)",
                       (bid, p.full_name.strip(), p.age, p.gender, (p.passport_no or "").upper() or None,
                        s, seat_rows[s]["price_add"], flight["fare"]))
            db.execute("UPDATE flight_seats SET status='HELD',hold_until=?,booking_id=? WHERE id=?",
                       (hold_until, bid, seat_rows[s]["id"]))
    return booking_dict(db, pnr)


def booking_dict(db, pnr: str, user_id: int | None = None) -> dict:
    fl.release_expired_holds(db)
    b = db.execute("SELECT * FROM bookings WHERE pnr=?", (pnr.upper(),)).fetchone()
    if not b or (user_id is not None and b["user_id"] != user_id):
        raise HTTPException(404, "Booking not found.")
    flight = db.execute("SELECT * FROM flights WHERE id=?", (b["flight_id"],)).fetchone()
    fd = fl.flight_dict(db, flight, with_seats=False)
    pax = [dict(r) for r in db.execute("SELECT * FROM passengers WHERE booking_id=? ORDER BY id", (b["id"],))]
    pay = db.execute("SELECT * FROM payments WHERE booking_id=? AND kind='PAYMENT' AND status='SUCCESS' "
                     "ORDER BY id DESC LIMIT 1", (b["id"],)).fetchone()
    out = {k: b[k] for k in b.keys() if k not in ("id", "user_id", "flight_id")}
    out.update(flight=fd, passengers=pax,
               payment={"method": pay["method"], "txn_ref": pay["txn_ref"], "upi_id": pay["upi_id"],
                        "card_last4": pay["card_last4"], "bank": pay["bank"]} if pay else None)
    out["cancel_quote"] = cancel_quote(db, b, flight) if b["status"] == "CONFIRMED" else None
    return out


def cancel_quote(db, b, flight) -> dict:
    o = fl.get_airport(db, flight["origin"])
    hours = (fl.depart_utc(flight["dep_local"], o["tz_minutes"]) - datetime.now(timezone.utc)).total_seconds() / 3600
    if hours <= 0:
        return {"allowed": False, "reason": "This flight has already departed.", "percent": 0, "refund": 0}
    pct = 90 if hours >= 48 else 70 if hours >= 24 else 40 if hours >= 4 else 0
    return {"allowed": True, "percent": pct, "refund": float(round(b["total"] * pct / 100)),
            "hours_to_departure": round(hours, 1),
            "policy": "90% refund 48h+ before departure · 70% at 24–48h · 40% at 4–24h · none within 4h"}


def confirm_booking(db, booking_id: int) -> None:
    with transaction(db):
        b = db.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if b["status"] == "CONFIRMED":
            return
        db.execute("UPDATE bookings SET status='CONFIRMED',confirmed_at=?,hold_until=NULL WHERE id=?",
                   (now_iso(), booking_id))
        db.execute("UPDATE flight_seats SET status='BOOKED',hold_until=NULL WHERE booking_id=?", (booking_id,))
        for p in db.execute("SELECT id FROM passengers WHERE booking_id=?", (booking_id,)).fetchall():
            tn = "098" + "".join(str(random.randint(0, 9)) for _ in range(10))
            db.execute("UPDATE passengers SET ticket_number=? WHERE id=?", (tn, p["id"]))


def cancel_booking(db, user_id: int, pnr: str) -> dict:
    with transaction(db):
        b = db.execute("SELECT * FROM bookings WHERE pnr=? AND user_id=?", (pnr.upper(), user_id)).fetchone()
        if not b:
            raise HTTPException(404, "Booking not found.")
        if b["status"] in ("CANCELLED", "EXPIRED"):
            raise HTTPException(400, "This booking is already cancelled.")
        flight = db.execute("SELECT * FROM flights WHERE id=?", (b["flight_id"],)).fetchone()
        now = now_iso()
        if b["status"] == "PENDING_PAYMENT":
            db.execute("UPDATE bookings SET status='CANCELLED',cancelled_at=?,refund_amount=0,refund_percent=0 WHERE id=?",
                       (now, b["id"]))
            db.execute("UPDATE flight_seats SET status='AVAILABLE',hold_until=NULL,booking_id=NULL WHERE booking_id=?",
                       (b["id"],))
            return {"refund": 0, "percent": 0}
        q = cancel_quote(db, b, flight)
        if not q["allowed"]:
            raise HTTPException(400, q["reason"])
        db.execute("UPDATE bookings SET status='CANCELLED',cancelled_at=?,refund_amount=?,refund_percent=? WHERE id=?",
                   (now, q["refund"], q["percent"], b["id"]))
        db.execute("UPDATE flight_seats SET status='AVAILABLE',hold_until=NULL,booking_id=NULL WHERE booking_id=?",
                   (b["id"],))
        if q["refund"] > 0:
            orig = db.execute("SELECT method FROM payments WHERE booking_id=? AND kind='PAYMENT' AND status='SUCCESS' "
                              "ORDER BY id DESC LIMIT 1", (b["id"],)).fetchone()
            db.execute("INSERT INTO payments(booking_id,kind,method,amount,status,txn_ref,created_at,updated_at)"
                       " VALUES (?,?,?,?,?,?,?,?)",
                       (b["id"], "REFUND", orig["method"] if orig else "UPI", q["refund"], "SUCCESS",
                        "RFND" + secrets.token_hex(5).upper(), now, now))
        return {"refund": q["refund"], "percent": q["percent"]}
