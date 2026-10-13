"""SQLite persistence. The schema is created automatically on first start."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS airports(
  code TEXT PRIMARY KEY, city TEXT NOT NULL, name TEXT NOT NULL,
  country TEXT NOT NULL, country_code TEXT NOT NULL,
  lat REAL NOT NULL, lon REAL NOT NULL, tz_minutes INTEGER NOT NULL,
  region TEXT NOT NULL, is_small INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS airlines(
  code TEXT PRIMARY KEY, name TEXT NOT NULL, tier REAL NOT NULL, hub TEXT
);
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL, phone TEXT, dob TEXT, gender TEXT,
  nationality TEXT, passport_no TEXT,
  created_at TEXT NOT NULL, last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS flights(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flight_number TEXT NOT NULL, airline_code TEXT NOT NULL REFERENCES airlines(code),
  origin TEXT NOT NULL REFERENCES airports(code),
  destination TEXT NOT NULL REFERENCES airports(code),
  dep_local TEXT NOT NULL, arr_local TEXT NOT NULL,
  duration_min INTEGER NOT NULL, stops INTEGER NOT NULL DEFAULT 0, via TEXT,
  base_fare REAL NOT NULL, fare REAL NOT NULL, prev_fare REAL NOT NULL,
  aircraft TEXT NOT NULL, layout TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'SCHEDULED',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE(flight_number, origin, destination, dep_local)
);
CREATE INDEX IF NOT EXISTS idx_flights_route ON flights(origin, destination, dep_local);
CREATE TABLE IF NOT EXISTS flight_seats(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flight_id INTEGER NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
  seat_no TEXT NOT NULL, row_no INTEGER NOT NULL, col TEXT NOT NULL,
  cabin TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'standard', price_add REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'AVAILABLE',      -- AVAILABLE | HELD | BOOKED | OCCUPIED
  hold_until TEXT, booking_id INTEGER,
  UNIQUE(flight_id, seat_no)
);
CREATE INDEX IF NOT EXISTS idx_seats_flight ON flight_seats(flight_id, status);
CREATE TABLE IF NOT EXISTS bookings(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pnr TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL REFERENCES users(id),
  flight_id INTEGER NOT NULL REFERENCES flights(id),
  status TEXT NOT NULL,                          -- PENDING_PAYMENT | CONFIRMED | CANCELLED | EXPIRED
  pax_count INTEGER NOT NULL,
  base_amount REAL NOT NULL, seat_amount REAL NOT NULL, taxes REAL NOT NULL,
  discount REAL NOT NULL DEFAULT 0, total REAL NOT NULL, promo_code TEXT,
  contact_email TEXT NOT NULL, contact_phone TEXT NOT NULL,
  hold_until TEXT, created_at TEXT NOT NULL, confirmed_at TEXT, cancelled_at TEXT,
  refund_amount REAL, refund_percent INTEGER
);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id, created_at);
CREATE TABLE IF NOT EXISTS passengers(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL, age INTEGER NOT NULL, gender TEXT,
  passport_no TEXT, seat_no TEXT NOT NULL, seat_price REAL NOT NULL DEFAULT 0,
  fare REAL NOT NULL, ticket_number TEXT
);
CREATE TABLE IF NOT EXISTS payments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  booking_id INTEGER NOT NULL REFERENCES bookings(id),
  kind TEXT NOT NULL DEFAULT 'PAYMENT',          -- PAYMENT | REFUND
  method TEXT NOT NULL, upi_id TEXT, card_last4 TEXT, bank TEXT,
  amount REAL NOT NULL,
  status TEXT NOT NULL,                          -- PENDING | SUCCESS | FAILED
  txn_ref TEXT NOT NULL, failure_reason TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fare_alerts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  email TEXT NOT NULL,
  origin TEXT NOT NULL, destination TEXT NOT NULL, travel_date TEXT NOT NULL,
  flight_id INTEGER REFERENCES flights(id),      -- NULL = cheapest fare on the route/date
  target_price REAL,
  baseline_price REAL NOT NULL, last_notified_price REAL NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, last_notified_at TEXT, notify_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS fare_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flight_id INTEGER NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
  fare REAL NOT NULL, recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fare_history ON fare_history(flight_id, recorded_at);
CREATE TABLE IF NOT EXISTS promos(
  code TEXT PRIMARY KEY, kind TEXT NOT NULL, value REAL NOT NULL,
  max_discount REAL, min_amount REAL NOT NULL DEFAULT 0,
  international_only INTEGER NOT NULL DEFAULT 0,
  first_booking_only INTEGER NOT NULL DEFAULT 0,
  description TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS email_outbox(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  to_email TEXT NOT NULL, subject TEXT NOT NULL, body_html TEXT NOT NULL,
  mode TEXT NOT NULL, status TEXT NOT NULL, error TEXT, file_path TEXT, created_at TEXT NOT NULL
);
"""

# code, city, name, country, cc, lat, lon, tz_minutes (fixed standard offset), region, small
AIRPORTS = [
    ("DEL", "Delhi", "Indira Gandhi International Airport", "India", "IN", 28.5562, 77.1000, 330, "IN", 0),
    ("BOM", "Mumbai", "Chhatrapati Shivaji Maharaj International Airport", "India", "IN", 19.0896, 72.8656, 330, "IN", 0),
    ("BLR", "Bengaluru", "Kempegowda International Airport", "India", "IN", 13.1986, 77.7066, 330, "IN", 0),
    ("MAA", "Chennai", "Chennai International Airport", "India", "IN", 12.9941, 80.1709, 330, "IN", 0),
    ("HYD", "Hyderabad", "Rajiv Gandhi International Airport", "India", "IN", 17.2403, 78.4294, 330, "IN", 0),
    ("CCU", "Kolkata", "Netaji Subhas Chandra Bose International Airport", "India", "IN", 22.6547, 88.4467, 330, "IN", 0),
    ("COK", "Kochi", "Cochin International Airport", "India", "IN", 10.1520, 76.4019, 330, "IN", 0),
    ("GOI", "Goa", "Dabolim Airport", "India", "IN", 15.3808, 73.8314, 330, "IN", 0),
    ("AMD", "Ahmedabad", "Sardar Vallabhbhai Patel International Airport", "India", "IN", 23.0772, 72.6347, 330, "IN", 0),
    ("PNQ", "Pune", "Pune Airport", "India", "IN", 18.5821, 73.9197, 330, "IN", 0),
    ("JAI", "Jaipur", "Jaipur International Airport", "India", "IN", 26.8242, 75.8122, 330, "IN", 0),
    ("LKO", "Lucknow", "Chaudhary Charan Singh International Airport", "India", "IN", 26.7606, 80.8893, 330, "IN", 0),
    ("TRV", "Thiruvananthapuram", "Trivandrum International Airport", "India", "IN", 8.4821, 76.9200, 330, "IN", 0),
    ("CCJ", "Kozhikode", "Calicut International Airport", "India", "IN", 11.1368, 75.9553, 330, "IN", 0),
    ("IXG", "Belagavi", "Belagavi Airport", "India", "IN", 15.8593, 74.6183, 330, "IN", 1),
    ("HBX", "Hubballi", "Hubballi Airport", "India", "IN", 15.3617, 75.0849, 330, "IN", 1),
    ("IXE", "Mangaluru", "Mangaluru International Airport", "India", "IN", 12.9613, 74.8901, 330, "IN", 0),
    ("VTZ", "Visakhapatnam", "Visakhapatnam Airport", "India", "IN", 17.7212, 83.2245, 330, "IN", 0),
    ("GAU", "Guwahati", "Lokpriya Gopinath Bordoloi International Airport", "India", "IN", 26.1061, 91.5859, 330, "IN", 0),
    ("DXB", "Dubai", "Dubai International Airport", "United Arab Emirates", "AE", 25.2532, 55.3657, 240, "gulf", 0),
    ("AUH", "Abu Dhabi", "Zayed International Airport", "United Arab Emirates", "AE", 24.4330, 54.6511, 240, "gulf", 0),
    ("DOH", "Doha", "Hamad International Airport", "Qatar", "QA", 25.2731, 51.6081, 180, "gulf", 0),
    ("SIN", "Singapore", "Singapore Changi Airport", "Singapore", "SG", 1.3644, 103.9915, 480, "se_asia", 0),
    ("KUL", "Kuala Lumpur", "Kuala Lumpur International Airport", "Malaysia", "MY", 2.7456, 101.7099, 480, "se_asia", 0),
    ("BKK", "Bangkok", "Suvarnabhumi Airport", "Thailand", "TH", 13.6900, 100.7501, 420, "se_asia", 0),
    ("HKG", "Hong Kong", "Hong Kong International Airport", "Hong Kong", "HK", 22.3080, 113.9185, 480, "east_asia", 0),
    ("NRT", "Tokyo", "Narita International Airport", "Japan", "JP", 35.7720, 140.3929, 540, "east_asia", 0),
    ("LHR", "London", "Heathrow Airport", "United Kingdom", "GB", 51.4700, -0.4543, 0, "europe", 0),
    ("CDG", "Paris", "Charles de Gaulle Airport", "France", "FR", 49.0097, 2.5479, 60, "europe", 0),
    ("FRA", "Frankfurt", "Frankfurt Airport", "Germany", "DE", 50.0379, 8.5622, 60, "europe", 0),
    ("IST", "Istanbul", "Istanbul Airport", "Turkey", "TR", 41.2753, 28.7519, 180, "europe", 0),
    ("JFK", "New York", "John F. Kennedy International Airport", "United States", "US", 40.6413, -73.7781, -300, "na", 0),
    ("SFO", "San Francisco", "San Francisco International Airport", "United States", "US", 37.6213, -122.3790, -480, "na", 0),
    ("SYD", "Sydney", "Sydney Kingsford Smith Airport", "Australia", "AU", -33.9399, 151.1753, 600, "oceania", 0),
    ("CMB", "Colombo", "Bandaranaike International Airport", "Sri Lanka", "LK", 7.1808, 79.8841, 330, "south_asia", 0),
    ("KTM", "Kathmandu", "Tribhuvan International Airport", "Nepal", "NP", 27.6966, 85.3591, 345, "south_asia", 0),
    ("MLE", "Malé", "Velana International Airport", "Maldives", "MV", 4.1918, 73.5290, 300, "south_asia", 0),
    ("DAC", "Dhaka", "Hazrat Shahjalal International Airport", "Bangladesh", "BD", 23.8433, 90.4010, 360, "south_asia", 0),
]

# code, name, price tier, connecting hub
AIRLINES = [
    ("6E", "IndiGo", 0.92, None), ("AI", "Air India", 1.12, None),
    ("IX", "Air India Express", 0.95, None), ("QP", "Akasa Air", 0.94, None),
    ("SG", "SpiceJet", 0.90, None), ("EK", "Emirates", 1.18, "DXB"),
    ("QR", "Qatar Airways", 1.16, "DOH"), ("EY", "Etihad Airways", 1.12, "AUH"),
    ("SQ", "Singapore Airlines", 1.22, "SIN"), ("TG", "Thai Airways", 1.05, None),
    ("MH", "Malaysia Airlines", 1.03, None), ("BA", "British Airways", 1.20, None),
    ("LH", "Lufthansa", 1.18, None), ("AF", "Air France", 1.16, None),
    ("TK", "Turkish Airlines", 1.08, "IST"), ("CX", "Cathay Pacific", 1.18, None),
    ("JL", "Japan Airlines", 1.20, None), ("QF", "Qantas", 1.20, None),
    ("UL", "SriLankan Airlines", 0.98, None), ("UA", "United Airlines", 1.15, None),
]

PROMOS = [
    ("SKYDROP", "PERCENT", 5, 500, 2000, 0, 0, "5% off, up to ₹500 — sent with fare-drop alerts"),
    ("WELCOME300", "FLAT", 300, None, 2500, 0, 1, "₹300 off your first booking"),
    ("INTL1000", "FLAT", 1000, None, 25000, 1, 0, "₹1,000 off international trips above ₹25,000"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


@contextmanager
def session():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def get_db():
    """FastAPI dependency: one connection per request."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection):
    """BEGIN IMMEDIATE so two people cannot grab the same seat at once."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def init_db() -> None:
    with session() as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR IGNORE INTO airports VALUES (?,?,?,?,?,?,?,?,?,?)", AIRPORTS)
        conn.executemany("INSERT OR IGNORE INTO airlines VALUES (?,?,?,?)", AIRLINES)
        conn.executemany(
            "INSERT OR IGNORE INTO promos(code,kind,value,max_discount,min_amount,"
            "international_only,first_booking_only,description) VALUES (?,?,?,?,?,?,?,?)", PROMOS)
