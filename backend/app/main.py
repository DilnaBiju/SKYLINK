import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config, fares
from .db import init_db
from .routers import alerts, auth, bookings, flights, payments


async def _fare_loop():
    while True:
        await asyncio.sleep(config.FARE_TICK_SECONDS)
        try:
            await asyncio.to_thread(fares.run_cycle)
        except Exception as exc:  # keep the watcher alive
            print(f"[fares] cycle failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(_fare_loop()) if config.FARE_WATCHER else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="SkyLink API", version="2.0.0", lifespan=lifespan,
              description="Flight search, seat selection, sandbox payments, tickets and fare-drop alerts.")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
for r in (auth, flights, bookings, payments, alerts):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "database": "sqlite", "email": "smtp" if config.SMTP_HOST else "saved to backend/outbox",
            "fare_watcher_seconds": config.FARE_TICK_SECONDS if config.FARE_WATCHER else None}
