"""Fare movement + fare-drop alerts.

`reprice_tick` nudges fares of upcoming flights (simulating market movement) and
stores each change in fare_history. `check_alerts` then emails anyone whose
tracked fare dropped. With a real fare feed you would replace only `reprice_tick`.
"""
import random
import sqlite3
from datetime import datetime, timezone

from . import emails, flights as fl
from .db import now_iso, session
from .mailer import send_email

MIN_DROP = 0.02  # must be at least 2% below the last price we told the user about


def _set_fare(db, row, new: float, now: str) -> None:
    db.execute("UPDATE flights SET prev_fare=fare, fare=?, updated_at=? WHERE id=?", (new, now, row["id"]))
    db.execute("INSERT INTO fare_history(flight_id,fare,recorded_at) VALUES (?,?,?)", (row["id"], new, now))


def reprice_tick(db: sqlite3.Connection) -> int:
    now, changed = now_iso(), 0
    rows = db.execute("SELECT * FROM flights WHERE status='SCHEDULED'").fetchall()
    cutoff = datetime.now(timezone.utc)
    for r in rows:
        o = fl.get_airport(db, r["origin"])
        if fl.depart_utc(r["dep_local"], o["tz_minutes"]) < cutoff:
            continue
        delta = max(-0.09, min(0.09, random.gauss(-0.004, 0.035)))
        new = round(r["fare"] * (1 + delta) / 10) * 10
        new = max(round(r["base_fare"] * 0.7 / 10) * 10, min(round(r["base_fare"] * 1.8 / 10) * 10, new))
        if new != r["fare"]:
            _set_fare(db, r, new, now)
            changed += 1
    return changed


def current_price(db, alert) -> tuple[float, sqlite3.Row] | None:
    if alert["flight_id"]:
        row = db.execute("SELECT * FROM flights WHERE id=? AND status='SCHEDULED'", (alert["flight_id"],)).fetchone()
    else:
        row = db.execute(
            "SELECT * FROM flights WHERE origin=? AND destination=? AND substr(dep_local,1,10)=? "
            "AND status='SCHEDULED' ORDER BY fare LIMIT 1",
            (alert["origin"], alert["destination"], alert["travel_date"])).fetchone()
    if not row:
        return None
    o = fl.get_airport(db, row["origin"])
    if fl.depart_utc(row["dep_local"], o["tz_minutes"]) < datetime.now(timezone.utc):
        return None
    return row["fare"], row


def check_alert(db, alert) -> dict | None:
    """Returns the email result if a notification was sent, else None."""
    found = current_price(db, alert)
    if not found:
        db.execute("UPDATE fare_alerts SET active=0 WHERE id=?", (alert["id"],))  # flight gone/departed
        return None
    price, row = found
    last = alert["last_notified_price"]
    if alert["target_price"] is not None:
        should = price <= alert["target_price"] and price < last   # at/under target and cheaper than last alert
    else:
        should = price <= last * (1 - MIN_DROP)
    if not should:
        if price > last:  # fare rose: raise the bar so a later fall is reported again
            db.execute("UPDATE fare_alerts SET last_notified_price=? WHERE id=?", (price, alert["id"]))
        return None
    promo = dict(db.execute("SELECT * FROM promos WHERE code='SKYDROP'").fetchone())
    subject, html = emails.fare_drop(dict(alert), fl.flight_dict(db, row, with_seats=False), last, price, promo)
    result = send_email(alert["email"], subject, html)
    db.execute("UPDATE fare_alerts SET last_notified_price=?, last_notified_at=?, notify_count=notify_count+1 WHERE id=?",
               (price, now_iso(), alert["id"]))
    return {**result, "old": last, "new": price}


def check_all_alerts(db) -> int:
    sent = 0
    for a in db.execute("SELECT * FROM fare_alerts WHERE active=1").fetchall():
        if check_alert(db, a):
            sent += 1
    return sent


def run_cycle() -> dict:
    with session() as db:
        fl.release_expired_holds(db)
        changed = reprice_tick(db)
        sent = check_all_alerts(db)
    print(f"[fares] repriced {changed} flights, sent {sent} fare-drop emails")
    return {"repriced": changed, "emails": sent}


def force_drop(db, alert, percent: float = 10.0) -> dict | None:
    """Demo helper: cut the tracked fare by `percent` and run the normal alert check."""
    found = current_price(db, alert)
    if not found:
        return None
    _, row = found
    new = max(500.0, round(row["fare"] * (1 - percent / 100) / 10) * 10)
    _set_fare(db, row, new, now_iso())
    fresh = db.execute("SELECT * FROM fare_alerts WHERE id=?", (alert["id"],)).fetchone()
    return check_alert(db, fresh)
