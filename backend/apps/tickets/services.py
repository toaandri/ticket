import base64
import hashlib
import hmac
from io import BytesIO

import qrcode
from django.conf import settings
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .models import Ticket


def ticket_secret(ticket):
    # A separate purpose/key derivation avoids storing recoverable raw QR secrets.
    key = hmac.digest(settings.SECRET_KEY.encode(), b"ticket-qr-v1", "sha256")
    value = hmac.digest(key, f"{ticket.pk}:{ticket.version}".encode(), "sha256")
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def qr_url(ticket):
    return f"{settings.APP_BASE_URL.rstrip('/')}/gate?token={ticket_secret(ticket)}"


def issue_tickets_locked(order):
    for item in order.items.select_related("ticket_type").order_by("id"):
        for index in range(item.quantity):
            price = (index + 1) * item.total_minor // item.quantity - index * item.total_minor // item.quantity
            ticket = Ticket(
                order_item=item,
                admission_index=index,
                admission_price_minor=price,
                event=order.event,
                holder=order.user,
                ticket_type=item.ticket_type,
                event_seat=item.event_seat,
            )
            ticket.token_hash = hashlib.sha256(ticket_secret(ticket).encode()).hexdigest()
            ticket.save()


def qr_png(ticket):
    image = qrcode.make(qr_url(ticket))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def ticket_pdf(ticket):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(420, 595))
    pdf.setTitle(f"Ticket {ticket.public_code}")
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(32, 550, "Ticket / Demo admission")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(32, 510, ticket.event.title[:42])
    pdf.setFont("Helvetica", 11)
    from zoneinfo import ZoneInfo

    local_time = ticket.event.start_at.astimezone(ZoneInfo(ticket.event.event_timezone))
    lines = [
        local_time.strftime("%d %b %Y %H:%M %Z"),
        ticket.event.venue.name if ticket.event.venue else "Online / to be announced",
        ticket.ticket_type.name,
        f"Seat: {ticket.event_seat.seat.label}" if ticket.event_seat_id else "General admission",
        f"Code: {ticket.public_code}",
        f"Status: {ticket.status}",
    ]
    for index, text in enumerate(lines):
        pdf.drawString(32, 480 - index * 22, text[:60])
    pdf.drawImage(ImageReader(BytesIO(qr_png(ticket))), 95, 110, width=230, height=230)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(32, 65, "Synthetic event. Simulated payment. Keep this code private.")
    pdf.drawString(32, 48, "Online check-in required. Only a VALID ticket admits entry.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
