"""Flight schedules, fares and seat maps.

IMPORTANT: there is no airline/GDS feed in this project. Schedules and fares are
generated deterministically for any route + date (so the same search always gives
the same flights) and are then stored in the database, where the fare watcher
moves prices over time. Swap `ensure_flights()` for a real provider API to go live.
"""
import hashlib
import math
import random
import sqlite3
from datetime import date, datetime, timedelta, timezone

from .db import now_iso

POOLS = {
    "IN": ["6E", "AI", "IX", "QP", "SG"],
    "gulf": ["AI", "6E", "IX", "EK", "QR", "EY"],
    "se_asia": ["AI", "6E", "SQ", "TG", "MH", "IX"],
    "europe": ["AI", "BA", "LH", "AF", "EK", "QR", "TK"],
    "na": ["AI", "UA", "EK", "QR", "BA"],
    "oceania": ["AI", "QF", "SQ", "EK"],
    "east_asia": ["AI", "CX", "JL", "SQ"],
    "south_asia": ["AI", "6E", "UL"],
}
DOMESTIC_HUBS = ["BLR", "BOM", "DEL", "HYD", "MAA"]
MAX_DAYS_AHEAD = 330


def haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_airport(db, code):
    return db.execute("SELECT * FROM airports WHERE code=?", (code,)).fetchone()


def _dist(a, b) -> float:
    return haversine(a["lat"], a["lon"], b["lat"], b["lon"])


def depart_utc(dep_local: str, tz_minutes: int) -> datetime:
    return datetime.strptime(dep_local, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc) - timedelta(minutes=tz_minutes)


def validate_date(d: date):
    today = datetime.now(timezone.utc).date() - timedelta(days=1)  # tolerate timezone differences
    if d < today:
        return "Choose today or a future date."
    if d > today + timedelta(days=MAX_DAYS_AHEAD):
        return f"Flights can be searched up to {MAX_DAYS_AHEAD} days ahead."
    return None


def ensure_flights(db: sqlite3.Connection, origin: str, dest: str, date_str: str) -> None:
    """Create the day's schedule for a route if it does not exist yet."""
    exists = db.execute(
        "SELECT 1 FROM flights WHERE origin=? AND destination=? AND substr(dep_local,1,10)=? LIMIT 1",
        (origin, dest, date_str)).fetchone()
    if exists:
        return
    o, d = get_airport(db, origin), get_airport(db, dest)
    seed = int(hashlib.sha256(f"{origin}>{dest}@{date_str}".encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    dist = _dist(o, d)
    domestic = o["country_code"] == "IN" and d["country_code"] == "IN"
    foreign = d if o["country_code"] == "IN" else o
    pool = POOLS["IN"] if domestic else POOLS.get(foreign["region"], POOLS["gulf"])
    airlines = {r["code"]: r for r in db.execute("SELECT * FROM airlines")}

    n = 6 if domestic else 5
    hours = sorted(rng.sample(range(5, 24) if domestic else range(0, 24), n))
    choices = pool[:]
    rng.shuffle(choices)
    while len(choices) < n:
        choices.append(rng.choice(pool))

    travel = date.fromisoformat(date_str)
    days_out = (travel - datetime.now(timezone.utc).date()).days
    adv = 0.85 if days_out >= 45 else 0.95 if days_out >= 22 else 1.05 if days_out >= 8 else 1.2 if days_out >= 3 else 1.4
    weekend = 1.05 if travel.weekday() in (4, 6) else 1.0
    base = (1900 + dist * 3.1) if domestic else (6500 + dist * 4.6)

    used, now = set(), now_iso()
    for i in range(n):
        al = airlines[choices[i]]
        number = f"{al['code']} {rng.randint(100, 999) if domestic else rng.randint(1, 999)}"
        while number in used:
            number = f"{al['code']} {rng.randint(100, 999)}"
        used.add(number)
        hour, minute = hours[i], rng.choice(range(0, 60, 5))
        dep = datetime(travel.year, travel.month, travel.day, hour, minute)

        stops, via = 0, None
        hub = al["hub"]
        if hub and not domestic and hub not in (origin, dest) and foreign["region"] in ("europe", "na", "oceania", "east_asia"):
            stops, via = 1, hub
        elif domestic and (o["is_small"] or d["is_small"]) and dist > 900 and rng.random() < 0.6:
            stops, via = 1, rng.choice([h for h in DOMESTIC_HUBS if h not in (origin, dest)])

        if via:
            v = get_airport(db, via)
            route_km = (_dist(o, v) + _dist(v, d)) * 1.04
            layover = rng.choice(range(70, 165, 5))
        else:
            route_km, layover = dist * 1.04, 0
        speed = 780 if route_km < 1500 else 850
        duration = int(round((route_km / speed * 60 + 35 + layover) / 5) * 5)

        arr_utc = dep - timedelta(minutes=o["tz_minutes"]) + timedelta(minutes=duration)
        arr_local = arr_utc + timedelta(minutes=d["tz_minutes"])

        tod = 0.93 if hour < 7 or hour >= 22 else 1.08 if hour in (7, 8, 9, 17, 18, 19, 20) else 1.0
        fare = base * al["tier"] * tod * adv * weekend * (0.88 if stops else 1.0) * rng.uniform(0.94, 1.06)
        fare = round(fare / 10) * 10

        wide = (not domestic) and dist >= 4500
        aircraft = (rng.choice(["Boeing 787-9", "Airbus A350-900"]) if wide
                    else rng.choice(["Airbus A320neo", "Boeing 737-8"]) if domestic
                    else rng.choice(["Airbus A321neo", "Boeing 737-8"]))
        cur = db.execute(
            "INSERT OR IGNORE INTO flights(flight_number,airline_code,origin,destination,dep_local,arr_local,"
            "duration_min,stops,via,base_fare,fare,prev_fare,aircraft,layout,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (number, al["code"], origin, dest, dep.strftime("%Y-%m-%d %H:%M"), arr_local.strftime("%Y-%m-%d %H:%M"),
             duration, stops, via, fare, fare, fare, aircraft, "wide" if wide else "narrow", now, now))
        if cur.rowcount:
            fid = cur.lastrowid
            db.execute("INSERT INTO fare_history(flight_id,fare,recorded_at) VALUES (?,?,?)", (fid, fare, now))
            _create_seats(db, fid, rng, wide, fare, domestic)


def _create_seats(db, flight_id: int, rng: random.Random, wide: bool, fare: float, domestic: bool) -> None:
    biz_rows = 4 if wide else 3
    last_row = 34 if wide else 28
    legroom = {biz_rows + 1, biz_rows + 11, biz_rows + 12}
    legroom_fee = 399 if domestic else 899
    biz_fee = round(fare * 1.1 / 50) * 50
    taken = rng.uniform(0.2, 0.55)
    rows = []
    for r in range(1, last_row + 1):
        business = r <= biz_rows
        for col in (["A", "C", "D", "F"] if business else ["A", "B", "C", "D", "E", "F"]):
            if business:
                cabin, kind, add = "BUSINESS", "business", biz_fee
            elif r in legroom:
                cabin, kind, add = "ECONOMY", "legroom", legroom_fee
            else:
                cabin, kind, add = "ECONOMY", "standard", 0
            status = "OCCUPIED" if rng.random() < taken else "AVAILABLE"
            rows.append((flight_id, f"{r}{col}", r, col, cabin, kind, add, status))
    db.executemany(
        "INSERT INTO flight_seats(flight_id,seat_no,row_no,col,cabin,kind,price_add,status) VALUES (?,?,?,?,?,?,?,?)", rows)


def release_expired_holds(db: sqlite3.Connection) -> None:
    now = now_iso()
    db.execute("UPDATE bookings SET status='EXPIRED' WHERE status='PENDING_PAYMENT' AND hold_until<?", (now,))
    db.execute("UPDATE flight_seats SET status='AVAILABLE',hold_until=NULL,booking_id=NULL "
               "WHERE status='HELD' AND hold_until<?", (now,))


def flight_dict(db, row, with_seats: bool = True) -> dict:
    o, d = get_airport(db, row["origin"]), get_airport(db, row["destination"])
    al = db.execute("SELECT name FROM airlines WHERE code=?", (row["airline_code"],)).fetchone()
    via = get_airport(db, row["via"]) if row["via"] else None
    out = {
        "id": row["id"], "flight_number": row["flight_number"],
        "airline_code": row["airline_code"], "airline": al["name"] if al else row["airline_code"],
        "origin": row["origin"], "origin_city": o["city"], "origin_airport": o["name"],
        "destination": row["destination"], "destination_city": d["city"], "destination_airport": d["name"],
        "departure": row["dep_local"].replace(" ", "T"), "arrival": row["arr_local"].replace(" ", "T"),
        "duration_min": row["duration_min"], "stops": row["stops"],
        "via": row["via"], "via_city": via["city"] if via else None,
        "fare": row["fare"], "prev_fare": row["prev_fare"], "base_fare": row["base_fare"],
        "aircraft": row["aircraft"], "layout": row["layout"], "status": row["status"],
        "international": not (o["country_code"] == "IN" and d["country_code"] == "IN"),
        "arrives_next_day": row["arr_local"][:10] != row["dep_local"][:10],
    }
    if with_seats:
        out["available_seats"] = db.execute(
            "SELECT COUNT(*) FROM flight_seats WHERE flight_id=? AND status='AVAILABLE'", (row["id"],)).fetchone()[0]
    return out


def search(db, origin: str, dest: str, date_str: str) -> list[dict]:
    release_expired_holds(db)
    ensure_flights(db, origin, dest, date_str)
    rows = db.execute(
        "SELECT * FROM flights WHERE origin=? AND destination=? AND substr(dep_local,1,10)=? "
        "AND status='SCHEDULED' ORDER BY fare", (origin, dest, date_str)).fetchall()
    cutoff = datetime.now(timezone.utc) + timedelta(hours=2)
    out = []
    for r in rows:
        o = get_airport(db, r["origin"])
        if depart_utc(r["dep_local"], o["tz_minutes"]) < cutoff:
            continue  # already left / boarding
        out.append(flight_dict(db, r))
    return out


def seat_map(db, flight_id: int) -> list[dict]:
    release_expired_holds(db)
    rows = db.execute("SELECT * FROM flight_seats WHERE flight_id=? ORDER BY row_no, col", (flight_id,)).fetchall()
    by_row: dict[int, dict] = {}
    for s in rows:
        r = by_row.setdefault(s["row_no"], {"row": s["row_no"], "cabin": s["cabin"], "seats": []})
        r["seats"].append({"seat_no": s["seat_no"], "col": s["col"], "kind": s["kind"],
                           "price_add": s["price_add"],
                           "available": s["status"] == "AVAILABLE"})
    return list(by_row.values())
