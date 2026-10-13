-- Schema actually used by the app (SQLite). Created automatically on first start.

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
