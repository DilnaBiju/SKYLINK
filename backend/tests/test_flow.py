import os
import tempfile
from datetime import date, timedelta

_d = tempfile.mkdtemp()
os.environ.update(DATABASE_PATH=_d + "/t.db", OUTBOX_DIR=_d + "/outbox", FARE_WATCHER="false")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def test_full_journey():
    day = (date.today() + timedelta(days=20)).isoformat()
    with TestClient(app) as c:
        r = c.post("/api/auth/register", json={"full_name": "Ravi Kumar", "email": "ravi@example.com",
                                               "password": "password1", "phone": "+919999999999"})
        assert r.status_code == 201
        H = {"Authorization": "Bearer " + r.json()["token"]}
        assert c.post("/api/auth/login", json={"email": "ravi@example.com", "password": "bad"}).status_code == 401

        intl = c.get("/api/flights/search", params=dict(origin="DEL", destination="LHR", date=day)).json()
        assert intl["international"] is True and intl["flights"]

        f = c.get("/api/flights/search", params=dict(origin="DEL", destination="BOM", date=day)).json()["flights"][0]
        rows = c.get(f"/api/flights/{f['id']}/seats").json()["rows"]
        free = [s["seat_no"] for r_ in rows for s in r_["seats"] if s["available"]]
        pax = [{"full_name": "Ravi Kumar", "age": 30, "gender": "Male", "seat_no": free[0]},
               {"full_name": "Asha Kumar", "age": 28, "gender": "Female", "seat_no": free[1]}]
        body = {"flight_id": f["id"], "passengers": pax, "contact_email": "ravi@example.com",
                "contact_phone": "+919999999999"}
        b = c.post("/api/bookings", json=body, headers=H)
        assert b.status_code == 201
        pnr = b.json()["pnr"]
        assert c.post("/api/bookings", json=body, headers=H).status_code == 409   # seats are held

        p = c.post("/api/payments/start", json={"pnr": pnr, "method": "UPI", "upi_id": "ravi@okaxis"}, headers=H).json()
        assert p["status"] == "PENDING"
        c.post(f"/api/payments/{p['payment_id']}/sandbox-resolve", json={"outcome": "approve"}, headers=H)
        bk = c.get(f"/api/bookings/{pnr}", headers=H).json()
        assert bk["status"] == "CONFIRMED" and bk["passengers"][0]["ticket_number"]
        assert c.get(f"/api/bookings/{pnr}/ticket.pdf", headers=H).content.startswith(b"%PDF")

        a = c.post("/api/alerts", json={"origin": "DEL", "destination": "BOM", "travel_date": day,
                                        "flight_id": f["id"]}, headers=H).json()
        d = c.post(f"/api/alerts/{a['id']}/simulate-drop", headers=H).json()
        assert d["new"] < d["old"]

        cancelled = c.post(f"/api/bookings/{pnr}/cancel", headers=H).json()
        assert cancelled["status"] == "CANCELLED" and cancelled["refund_amount"] > 0
        assert os.listdir(_d + "/outbox")  # confirmation, fare-drop, cancellation emails were produced
