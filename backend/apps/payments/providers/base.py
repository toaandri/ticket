from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentResult:
    provider_id: str
    status: str
    checkout_url: str = ""


class PaymentProvider(Protocol):
    def create_payment(self, payment, scenario: str = "success") -> PaymentResult: ...
    def fetch_status(self, payment) -> str: ...
    def refund(self, payment, amount: int, key: str) -> str: ...
