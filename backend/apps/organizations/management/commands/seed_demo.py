import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.checkins.services import check_in
from apps.events.models import Event
from apps.events.services import (
    cancel_event,
    configure_ticket_type,
    create_event,
    publish_event,
    refund_cancelled_events,
)
from apps.orders.services import create_order
from apps.organizations.models import EventStaffAssignment, Membership, Organization
from apps.organizations.services import create_organization
from apps.payments.services import initiate_payment, refund_order
from apps.promotions.models import Promotion
from apps.reservations.services import create_hold
from apps.tickets.models import Ticket
from apps.tickets.services import ticket_secret
from apps.venues.services import add_seats, add_section, create_venue


class Command(BaseCommand):
    help = "Create deterministic synthetic demo fixtures in DEBUG mode; preserve financial/audit history."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Demo account password; generated on first run if omitted.")
        parser.add_argument(
            "--reset-demo",
            action="store_true",
            help="Create a new synthetic dataset without deleting historical transactions.",
        )
        parser.add_argument("--confirm-reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo seeding is disabled unless DEBUG=True.")
        prefix = "demo"
        if options["reset_demo"]:
            if not options["confirm_reset"]:
                raise CommandError(
                    "--reset-demo requires --confirm-reset. Existing orders and audit remain preserved."
                )
            prefix = f"demo{Organization.objects.filter(slug__startswith='demo', name__startswith='[SYNTHETIC]').count() // 3 + 1}"
        if Organization.objects.filter(slug=f"{prefix}-studio").exists():
            self.stdout.write("Demo already exists. No data or passwords changed.")
            return
        password = options["password"] or secrets.token_urlsafe(18)
        if len(password) < 12:
            raise CommandError("Use at least 12 characters for the demo password.")
        now = timezone.now().replace(microsecond=0)
        users = {}
        for role in ["owner", "manager", "editor", "finance", "scanner", "attendee"]:
            email = f"{prefix}-{role}@ticket.example"
            if User.objects.filter(email=email).exists():
                raise CommandError(
                    f"Account {email} exists outside this dataset. Choose a fresh development database."
                )
            users[role] = User.objects.create_user(
                email, password, display_name=f"Synthetic {role.title()}", email_verified_at=now
            )
        owner = users["owner"]
        orgs = [
            create_organization(owner=owner, name=f"[SYNTHETIC] {name}", slug=f"{prefix}-{slug}")
            for name, slug in [("Studio Collective", "studio"), ("City Stage", "city"), ("Lab Sessions", "lab")]
        ]
        for role in ["manager", "editor", "finance", "scanner"]:
            Membership.objects.create(organization=orgs[0], user=users[role], role=role.upper())
        venues = []
        for index, name in enumerate(["Demo Garden Hall", "Demo Riverside Theatre", "Demo Race Room"]):
            venue = create_venue(
                actor=owner,
                organization_id=orgs[index].pk,
                name=name,
                city="Antananarivo",
                address="Synthetic address — no real venue",
                accessibility_info="Step-free entrance, accessible seating and quiet room.",
            )
            section = add_section(
                actor=owner, venue_id=venue.pk, code="main", name="Main seating", capacity=1 if index == 2 else 30
            )
            seats = [
                {
                    "row_label": chr(65 + n // 10),
                    "seat_number": n % 10 + 1,
                    "label": f"{chr(65 + n // 10)}{n % 10 + 1}",
                    "accessible": n < 2,
                }
                for n in range(section.capacity)
            ]
            add_seats(actor=owner, venue_id=venue.pk, section_id=section.pk, seats=seats)
            venues.append((venue, section))
        names = [
            "Garden Sessions",
            "An Evening on Stage",
            "Creative Futures",
            "Open Air Stories",
            "The Sunday Matinee",
            "One Seat Race Lab",
            "Yesterday's Gathering",
            "Cancelled Demo Night",
        ]
        events = []
        for index, name in enumerate(names):
            org_index = 2 if index == 5 else index % 3
            venue, section = venues[org_index]
            mode = "MIXED" if index in [2, 5] else "ASSIGNED" if index in [1, 4] else "GENERAL"
            event = create_event(
                actor=owner,
                organization_id=orgs[org_index].pk,
                venue_id=venue.pk,
                slug=f"event-{index + 1}",
                title=name,
                description="A synthetic community event for the Ticket portfolio demo. All payments are simulated.",
                category=["Music", "Theatre", "Technology"][index % 3],
                start_at=now + timedelta(days=index + 2),
                end_at=now + timedelta(days=index + 2, hours=3),
                sales_start_at=now - timedelta(days=1),
                sales_end_at=now + timedelta(days=index + 1),
                seating_mode=mode,
            )
            if mode in ["GENERAL", "MIXED"]:
                configure_ticket_type(
                    actor=owner,
                    event_id=event.pk,
                    code="general",
                    name="General admission",
                    kind="GENERAL",
                    price_minor=1500 + index * 250,
                    currency="EUR",
                    quota=2 if index == 5 else 40,
                    per_order_limit=10,
                )
            if mode in ["ASSIGNED", "MIXED"]:
                configure_ticket_type(
                    actor=owner,
                    event_id=event.pk,
                    code="reserved",
                    name="Reserved seating",
                    kind="ASSIGNED",
                    venue_section_id=section.pk,
                    price_minor=2500 + index * 250,
                    currency="EUR",
                    quota=section.capacity,
                    per_order_limit=10,
                )
            event = publish_event(actor=owner, event_id=event.pk)
            events.append(event)
            if org_index == 0:
                EventStaffAssignment.objects.create(
                    event=event, membership=Membership.objects.get(organization=orgs[0], user=users["scanner"])
                )
        Promotion.objects.create(
            organization=orgs[0],
            event=events[0],
            code="DEMO10",
            kind="PERCENT",
            amount=10,
            currency="EUR",
            usage_limit=50,
            per_user_limit=1,
            start_at=now - timedelta(days=1),
            end_at=now + timedelta(days=10),
        )
        # Use the same transaction services as clients; no fixture bypass of inventory.
        for index in [0, 6, 7]:
            event = events[index]
            ticket_type = event.ticket_types.get(kind="GENERAL")
            hold = create_hold(
                actor=users["attendee"],
                event_id=event.pk,
                items=[{"ticket_type_id": str(ticket_type.pk), "quantity": 3}],
                key=f"{prefix}-hold-{index}",
            )
            order = create_order(actor=users["attendee"], reservation_id=hold.pk, key=f"{prefix}-order-{index}")
            initiate_payment(actor=users["attendee"], order_id=order.pk, key=f"{prefix}-payment-{index}")
            if index == 0:
                ticket = Ticket.objects.filter(order_item__order=order).first()
                refund_order(
                    actor=owner,
                    order_id=order.pk,
                    ticket_ids=[ticket.pk],
                    reason="Synthetic partial refund",
                    key=f"{prefix}-refund",
                )
            if index == 6:
                Event.objects.filter(pk=event.pk).update(
                    start_at=now - timedelta(minutes=30), end_at=now + timedelta(minutes=30)
                )
                ticket = Ticket.objects.filter(order_item__order=order).first()
                check_in(actor=users["scanner"], event_id=event.pk, token=ticket_secret(ticket), key=f"{prefix}-scan")
                Event.objects.filter(pk=event.pk).update(
                    start_at=now - timedelta(days=2), end_at=now - timedelta(days=2, hours=-3), status="COMPLETED"
                )
            if index == 7:
                cancel_event(actor=owner, event_id=event.pk)
        refund_cancelled_events()
        assigned = events[1].ticket_types.get(kind="ASSIGNED")
        seat = events[1].seats.first()
        create_hold(
            actor=owner,
            event_id=events[1].pk,
            items=[{"ticket_type_id": str(assigned.pk), "event_seat_id": str(seat.pk), "quantity": 1}],
            key=f"{prefix}-sample-hold",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created 3 synthetic organizations, 3 venues, 8 events and 6 verified demo accounts. Dataset: {prefix}"
            )
        )
        for user in users.values():
            self.stdout.write(f"{user.email} / {password}")
        self.stdout.write("These are development credentials, never production administrator credentials.")
