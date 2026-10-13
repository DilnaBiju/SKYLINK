from datetime import datetime
from html import escape as e

from .config import FRONTEND_URL


def inr(n) -> str:
    n = int(round(float(n)))
    s = f"{n:,}"
    if n >= 1000:  # Indian digit grouping
        head, tail = str(n)[:-3], str(n)[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return "₹" + s


def fmt_dt(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%a, %d %b %Y · %H:%M")


def _layout(title: str, body: str) -> str:
    return f"""<!doctype html><html><body style="margin:0;background:#eef2f8;font-family:Segoe UI,Arial,sans-serif;color:#0d1b3e">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border-radius:14px;overflow:hidden">
<tr><td style="background:#0d1b3e;padding:20px 28px;color:#fff;font-size:22px;font-weight:700">Sky<span style="color:#ffc83d">Link</span></td></tr>
<tr><td style="padding:28px"><h1 style="margin:0 0 14px;font-size:22px">{e(title)}</h1>{body}</td></tr>
<tr><td style="padding:18px 28px;background:#f5f7fb;color:#6b7893;font-size:12px">You received this email because of activity on your SkyLink account. This is an academic project: fares and tickets are simulated.</td></tr>
</table></td></tr></table></body></html>"""


def _btn(url: str, label: str) -> str:
    return (f'<a href="{e(url)}" style="display:inline-block;margin-top:18px;background:#ffc83d;color:#0d1b3e;'
            f'font-weight:700;text-decoration:none;padding:12px 22px;border-radius:8px">{e(label)}</a>')


def welcome(name: str) -> tuple[str, str]:
    body = (f"<p>Hi {e(name)}, your SkyLink account is ready. Search flights, pick your seats, pay with UPI "
            f"and get your ticket in minutes.</p>{_btn(FRONTEND_URL, 'Search flights')}")
    return "Welcome to SkyLink", _layout("Welcome aboard", body)


def password_reset(name: str, link: str) -> tuple[str, str]:
    body = (f"<p>Hi {e(name)}, use the button below to choose a new password. The link works for 30 minutes "
            f"and only once. If you did not ask for this, ignore this email.</p>{_btn(link, 'Reset password')}")
    return "Reset your SkyLink password", _layout("Reset your password", body)


def booking_confirmation(b: dict) -> tuple[str, str]:
    f = b["flight"]
    rows = "".join(
        f'<tr><td style="padding:6px 0">{e(p["full_name"])}</td><td>{e(p["seat_no"])}</td>'
        f'<td style="font-family:monospace">{e(p["ticket_number"] or "")}</td></tr>' for p in b["passengers"])
    body = f"""<p>Your booking is confirmed. Booking reference (PNR): <b style="font-size:20px;letter-spacing:2px">{e(b['pnr'])}</b></p>
<div style="background:#f5f7fb;border-radius:10px;padding:16px;margin:14px 0">
<div style="font-size:24px;font-weight:700">{e(f['origin'])} → {e(f['destination'])}</div>
<div style="color:#51607f">{e(f['origin_city'])} to {e(f['destination_city'])} · {e(f['airline'])} {e(f['flight_number'])}</div>
<div style="margin-top:8px">Departs {e(fmt_dt(f['departure']))} (local) · Arrives {e(fmt_dt(f['arrival']))} (local)</div></div>
<table width="100%" style="font-size:14px"><tr style="color:#6b7893;text-align:left"><th>Passenger</th><th>Seat</th><th>Ticket no.</th></tr>{rows}</table>
<p style="margin-top:16px">Total paid: <b>{inr(b['total'])}</b></p>
{_btn(f"{FRONTEND_URL}/trips/{b['pnr']}", 'View e-ticket')}"""
    return f"Booking confirmed · {b['pnr']} · {f['origin']}→{f['destination']}", _layout("You're booked", body)


def cancellation(b: dict) -> tuple[str, str]:
    f = b["flight"]
    refund = (f"<p>Refund: <b>{inr(b['refund_amount'])}</b> ({b['refund_percent']}%) to your original payment method "
              f"in 5–7 working days.</p>") if b.get("refund_amount") else "<p>No refund applies for this cancellation.</p>"
    body = (f"<p>Booking <b>{e(b['pnr'])}</b> ({e(f['origin'])} → {e(f['destination'])}, {e(fmt_dt(f['departure']))}) "
            f"has been cancelled.</p>{refund}{_btn(FRONTEND_URL, 'Book another flight')}")
    return f"Booking cancelled · {b['pnr']}", _layout("Booking cancelled", body)


def fare_drop(alert: dict, f: dict, old: float, new: float, promo: dict) -> tuple[str, str]:
    pct = round((old - new) / old * 100)
    link = (f"{FRONTEND_URL}/flights?from={f['origin']}&to={f['destination']}"
            f"&date={f['departure'][:10]}&pax=1")
    target = (f"<p style='color:#17a06b'><b>This is at or below your target of {inr(alert['target_price'])}.</b></p>"
              if alert.get("target_price") and new <= alert["target_price"] else "")
    body = f"""<p>Good news: the fare you are tracking just dropped.</p>
<div style="background:#f5f7fb;border-radius:10px;padding:16px;margin:14px 0">
<div style="font-size:22px;font-weight:700">{e(f['origin_city'])} → {e(f['destination_city'])}</div>
<div style="color:#51607f">{e(f['airline'])} {e(f['flight_number'])} · {e(fmt_dt(f['departure']))}</div>
<div style="margin-top:10px"><span style="text-decoration:line-through;color:#8a95ad">{inr(old)}</span>
&nbsp;<span style="font-size:28px;font-weight:800">{inr(new)}</span>
&nbsp;<span style="background:#dff6ec;color:#0f7a50;padding:3px 8px;border-radius:20px;font-weight:700">↓ {pct}%</span></div></div>
{target}
<div style="border:2px dashed #ffc83d;border-radius:10px;padding:14px;background:#fffaf0">
<b>Extra offer:</b> {e(promo['description'])}.<br>Use code
<b style="font-size:18px;letter-spacing:1px">{e(promo['code'])}</b> at checkout.</div>
<p style="color:#6b7893;font-size:13px">Fares change often. Seats are not held until you book.</p>
{_btn(link, 'Book at the new fare')}"""
    return f"Fare drop: {f['origin']}→{f['destination']} now {inr(new)} (↓{pct}%)", _layout("Fare dropped", body)
