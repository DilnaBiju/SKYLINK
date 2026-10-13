"""Central configuration. Values come from backend/.env (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def flag(key: str, default: bool = False) -> bool:
    return env(key, "true" if default else "false").lower() in ("1", "true", "yes", "on")


DB_PATH = Path(env("DATABASE_PATH", str(BASE_DIR / "data" / "skylink.db")))
OUTBOX_DIR = Path(env("OUTBOX_DIR", str(BASE_DIR / "outbox")))

JWT_SECRET = env("JWT_SECRET", "dev-only-secret-change-me-please-32-bytes")
TOKEN_HOURS = int(env("TOKEN_HOURS", "168"))

FRONTEND_URL = env("FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")
CORS_ORIGINS = [o.strip() for o in env(
    "CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if o.strip()]

# --- Email (SMTP). Leave SMTP_HOST empty to save emails to backend/outbox/ instead.
SMTP_HOST = env("SMTP_HOST")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER")
SMTP_PASSWORD = env("SMTP_PASSWORD")
SMTP_STARTTLS = flag("SMTP_STARTTLS", True)
SMTP_SSL = flag("SMTP_SSL", False)
MAIL_FROM = env("MAIL_FROM", "SkyLink <no-reply@skylink.local>")

# --- Fare watcher
FARE_TICK_SECONDS = int(env("FARE_TICK_SECONDS", "300"))   # how often fares are re-priced
FARE_WATCHER = flag("FARE_WATCHER", True)
DEV_TOOLS = flag("DEV_TOOLS", True)                         # "simulate fare drop" button

# --- Payments (sandbox only: no money moves)
SANDBOX_PAYMENTS = flag("SANDBOX_PAYMENTS", True)
SEAT_HOLD_MINUTES = int(env("SEAT_HOLD_MINUTES", "10"))
