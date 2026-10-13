import sqlite3
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import flights as fl
from ..db import get_db

router = APIRouter(prefix="/api", tags=["flights"])

POPULAR = [("DEL", "BOM"), ("BLR", "DEL"), ("COK", "DXB"), ("BOM", "SIN"),
           ("DEL", "LHR"), ("IXG", "BOM"), ("HYD", "DOH"), ("MAA", "BKK")]


@router.get("/airports")
def airports(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT code,city,name,country,country_code FROM airports ORDER BY city").fetchall()
    return [{**dict(r), "domestic": r["country_code"] == "IN"} for r in rows]


@router.get("/flights/search")
def search(origin: str = Query(min_length=3, max_length=3), destination: str = Query(min_length=3, max_length=3),
           date: date = Query(), pax: int = Query(1, ge=1, le=9), db: sqlite3.Connection = Depends(get_db)):
    origin, destination = origin.upper(), destination.upper()
    if origin == destination:
        raise HTTPException(400, "Origin and destination must be different.")
    if not fl.get_airport(db, origin) or not fl.get_airport(db, destination):
        raise HTTPException(404, "Unknown airport code.")
    err = fl.validate_date(date)
    if err:
        raise HTTPException(400, err)
    results = fl.search(db, origin, destination, date.isoformat())
    return {"flights": results, "pax": pax,
            "international": results[0]["international"] if results else None}


@router.get("/flights/popular")
def popular(db: sqlite3.Connection = Depends(get_db)):
    day = (datetime.now(timezone.utc).date() + timedelta(days=14)).isoformat()
    out = []
    for o, d in POPULAR:
        res = fl.search(db, o, d, day)
        if res:
            best = min(res, key=lambda f: f["fare"])
            out.append({"origin": o, "destination": d, "origin_city": best["origin_city"],
                        "destination_city": best["destination_city"], "date": day, "from_fare": best["fare"],
                        "departure": best["departure"][11:16], "flight_number": best["flight_number"],
                        "international": best["international"]})
    return out


def _get(db, flight_id):
    row = db.execute("SELECT * FROM flights WHERE id=?", (flight_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Flight not found.")
    return row


@router.get("/flights/{flight_id}")
def flight(flight_id: int, db: sqlite3.Connection = Depends(get_db)):
    fl.release_expired_holds(db)
    return fl.flight_dict(db, _get(db, flight_id))


@router.get("/flights/{flight_id}/seats")
def seats(flight_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = _get(db, flight_id)
    return {"flight": fl.flight_dict(db, row), "rows": fl.seat_map(db, flight_id)}


@router.get("/flights/{flight_id}/fare-history")
def fare_history(flight_id: int, db: sqlite3.Connection = Depends(get_db)):
    _get(db, flight_id)
    rows = db.execute("SELECT fare,recorded_at FROM fare_history WHERE flight_id=? ORDER BY id DESC LIMIT 30",
                      (flight_id,)).fetchall()
    return [dict(r) for r in reversed(rows)]
