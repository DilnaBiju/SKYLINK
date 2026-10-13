from datetime import datetime
from io import BytesIO

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

INK, GOLD, MUTED, LINE = HexColor("#0D1B3E"), HexColor("#FFC83D"), HexColor("#5B6B88"), HexColor("#DCE3EF")


def _inr(n) -> str:  # Helvetica has no rupee glyph
    return f"INR {int(round(float(n))):,}"


def _dt(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M")


def build_ticket_pdf(b: dict) -> bytes:
    f = b["flight"]
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setTitle(f"SkyLink e-ticket {b['pnr']}")

    c.setFillColor(INK)
    c.rect(0, h - 90, w, 90, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 26)
    c.drawString(40, h - 55, "Sky")
    c.setFillColor(GOLD)
    c.drawString(40 + c.stringWidth("Sky", "Helvetica-Bold", 26), h - 55, "Link")
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 40, h - 45, "E-TICKET / BOARDING INFORMATION")
    c.drawRightString(w - 40, h - 60, f"Booking reference (PNR): {b['pnr']}")

    y = h - 150
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 44)
    c.drawString(40, y, f["origin"])
    c.drawRightString(w - 40, y, f["destination"])
    c.setFont("Helvetica", 11)
    c.setFillColor(MUTED)
    c.drawString(40, y - 18, f["origin_city"])
    c.drawRightString(w - 40, y - 18, f["destination_city"])
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(150, y + 12, w - 150, y + 12)
    c.setFillColor(INK)
    stops = "Non-stop" if f["stops"] == 0 else f"1 stop via {f['via']}"
    c.drawCentredString(w / 2, y - 6, f"{f['duration_min'] // 60}h {f['duration_min'] % 60}m · {stops}")

    y -= 60
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(40, y, w - 40, y)
    y -= 26
    cols = [("FLIGHT", f"{f['airline']} {f['flight_number']}"), ("DEPARTS (LOCAL)", _dt(f["departure"])),
            ("ARRIVES (LOCAL)", _dt(f["arrival"])), ("STATUS", b["status"])]
    x = 40
    for label, val in cols:
        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        c.drawString(x, y, label)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(INK)
        c.drawString(x, y - 16, val)
        x += 135

    y -= 56
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Passengers")
    y -= 8
    c.line(40, y, w - 40, y)
    y -= 18
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    for x, t in ((40, "NAME"), (270, "AGE"), (320, "SEAT"), (380, "TICKET NUMBER")):
        c.drawString(x, y, t)
    c.setFillColor(INK)
    for p in b["passengers"]:
        y -= 20
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, p["full_name"].upper()[:34])
        c.setFont("Helvetica", 11)
        c.drawString(270, y, str(p["age"]))
        c.drawString(320, y, p["seat_no"])
        c.drawString(380, y, p["ticket_number"] or "-")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Payment summary")
    y -= 8
    c.line(40, y, w - 40, y)
    lines = [("Base fare", b["base_amount"]), ("Seat selection", b["seat_amount"]),
             ("Taxes & airport fees", b["taxes"])]
    if b["discount"]:
        lines.append((f"Discount ({b['promo_code']})", -b["discount"]))
    for label, amt in lines:
        y -= 18
        c.setFont("Helvetica", 10)
        c.drawString(40, y, label)
        c.drawRightString(w - 40, y, _inr(amt) if amt >= 0 else "- " + _inr(-amt))
    y -= 22
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Total paid")
    c.drawRightString(w - 40, y, _inr(b["total"]))

    qr = QrCodeWidget(f"SKYLINK|{b['pnr']}|{f['flight_number']}|{f['departure'][:10]}")
    x0, y0, x1, y1 = qr.getBounds()
    d = Drawing(110, 110, transform=[110 / (x1 - x0), 0, 0, 110 / (y1 - y0), 0, 0])
    d.add(qr)
    renderPDF.draw(d, c, 40, 90)
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawString(165, 150, "Show this e-ticket and a valid photo ID (passport for international flights)")
    c.drawString(165, 138, "at the airport. Report 2 hours before domestic and 3 hours before international departures.")
    c.drawString(165, 120, "Academic project: this document is a simulation and is not valid for air travel.")
    c.showPage()
    c.save()
    return buf.getvalue()
