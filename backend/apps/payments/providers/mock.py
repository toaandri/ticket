from .base import PaymentResult


class MockPaymentProvider:
    def create_payment(self, payment, scenario="success"):
        outcome = {
            "success": "SUCCEEDED",
            "decline": "FAILED",
            "pending": "PENDING",
            "timeout": "PENDING",
            "delayed": "PENDING",
        }[scenario]
        return PaymentResult(f"mock_{payment.pk}", outcome)

    def fetch_status(self, payment):
        return payment.status

    def refund(self, payment, amount, key):
        import hashlib

        return "mock_refund_" + hashlib.sha256(f"{payment.pk}:{amount}:{key}".encode()).hexdigest()[:32]
