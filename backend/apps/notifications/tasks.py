from celery import shared_task

from .services import enqueue_reminders, process_outbox


@shared_task
def deliver_outbox():
    return process_outbox()


@shared_task
def send_reminders():
    enqueue_reminders()


@shared_task
def maintain_inventory():
    from apps.payments.services import reconcile_payments
    from apps.reservations.services import expire_holds

    expire_holds()
    reconcile_payments()
