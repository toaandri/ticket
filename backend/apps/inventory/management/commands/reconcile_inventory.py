import json

from django.core.management.base import BaseCommand, CommandError

from apps.inventory.services import reconcile_inventory


class Command(BaseCommand):
    help = "Report inventory mismatches without modifying records. Nonzero exit on mismatch."

    def handle(self, *args, **options):
        mismatches = reconcile_inventory()
        self.stdout.write(json.dumps({"mismatches": mismatches}, indent=2))
        if mismatches:
            raise CommandError("Inventory reconciliation failed; review the recovery runbook.")
