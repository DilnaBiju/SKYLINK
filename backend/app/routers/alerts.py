import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from .. import config, fares, flights as fl
from ..db import get_db, now_iso
from ..schemas import AlertIn
from ..security import current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _alert_dict(db, a) -> dict:
    o, d = fl.get_airport(db, a["origin"]), fl.get_airport(db, a["destination"])
    out = {k: a[k] for k in a.keys() if k != "user_id"}
    out.update(origin_city=o["city"], destination_city=d["city"], flight_label=None, current_price=None)
    if a["flight_id"]:
        f = db.execute("SELECT flight_number, airline_code FROM flights WHERE id=?", (a["flight_id"],)).fetchone()
        out["flight_label"] = f["flight_number"] if f else None
    found = fares.current_price(db, a)
    if found:
        out["current_price"] = found[0]
    return out


@router.get("")
def list_alerts(user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM fare_alerts WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    return {"alerts": [_alert_dict(db, a) for a in rows], "dev_tools": config.DEV_TOOLS,
            "email_mode": "smtp" if config.SMTP_HOST else "file"}


@router.post("", status_code=201)
def create(body: AlertIn, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    o, d = body.origin.upper(), body.destination.upper()
    if o == d or not fl.get_airport(db, o) or not fl.get_airport(db, d):
        raise HTTPException(400, "Choose two different, valid airports.")
    err = fl.validate_date(body.travel_date)
    if err:
        raise HTTPException(400, err)
    ds = body.travel_date.isoformat()
    fl.ensure_flights(db, o, d, ds)
    if body.flight_id:
        f = db.execute("SELECT * FROM flights WHERE id=? AND origin=? AND destination=?", (body.flight_id, o, d)).fetchone()
        if not f:
            raise HTTPException(404, "Flight not found for this route.")
    dup = db.execute("SELECT id FROM fare_alerts WHERE user_id=? AND origin=? AND destination=? AND travel_date=? "
                     "AND IFNULL(flight_id,0)=? AND active=1",
                     (user["id"], o, d, ds, body.flight_id or 0)).fetchone()
    if dup:
        raise HTTPException(409, "You already track this. Open it below to change the target.")
    probe = {"flight_id": body.flight_id, "origin": o, "destination": d, "travel_date": ds}
    found = fares.current_price(db, probe)
    if not found:
        raise HTTPException(400, "No upcoming flights to track for that date.")
    price = found[0]
    cur = db.execute(
        "INSERT INTO fare_alerts(user_id,email,origin,destination,travel_date,flight_id,target_price,baseline_price,"
        "last_notified_price,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (user["id"], str(body.email or user["email"]), o, d, ds, body.flight_id, body.target_price, price, price, now_iso()))
    return _alert_dict(db, db.execute("SELECT * FROM fare_alerts WHERE id=?", (cur.lastrowid,)).fetchone())


def _mine(db, alert_id, user_id):
    a = db.execute("SELECT * FROM fare_alerts WHERE id=? AND user_id=?", (alert_id, user_id)).fetchone()
    if not a:
        raise HTTPException(404, "Alert not found.")
    return a


@router.delete("/{alert_id}", status_code=204)
def delete(alert_id: int, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    _mine(db, alert_id, user["id"])
    db.execute("DELETE FROM fare_alerts WHERE id=?", (alert_id,))


@router.post("/{alert_id}/toggle")
def toggle(alert_id: int, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    a = _mine(db, alert_id, user["id"])
    found = fares.current_price(db, a)
    new = 0 if a["active"] else 1
    if new and found:  # resume from today's price
        db.execute("UPDATE fare_alerts SET active=1,last_notified_price=? WHERE id=?", (found[0], alert_id))
    elif new:
        raise HTTPException(400, "This flight has already departed.")
    else:
        db.execute("UPDATE fare_alerts SET active=0 WHERE id=?", (alert_id,))
    return _alert_dict(db, db.execute("SELECT * FROM fare_alerts WHERE id=?", (alert_id,)).fetchone())


@router.post("/{alert_id}/simulate-drop")
def simulate_drop(alert_id: int, user=Depends(current_user), db: sqlite3.Connection = Depends(get_db)):
    """Demo tool: lowers the tracked fare ~10% and runs the real alert check, so you can show the email."""
    if not config.DEV_TOOLS:
        raise HTTPException(404, "Not found.")
    a = _mine(db, alert_id, user["id"])
    if not a["active"]:
        raise HTTPException(400, "Turn this alert on first.")
    result = fares.force_drop(db, a, 10.0)
    if not result:
        raise HTTPException(400, "The drop was too small to trigger an email, or the flight has departed.")
    return {"emailed": True, **result, "alert": _alert_dict(db, db.execute("SELECT * FROM fare_alerts WHERE id=?", (alert_id,)).fetchone())}
