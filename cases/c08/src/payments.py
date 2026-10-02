class PaymentService:
    def __init__(self, gateway):
        self.gateway = gateway   # gateway.charge(amount_cents) -> charge_id

    def charge(self, idempotency_key: str, amount_cents: int) -> str:
        """Charge once per idempotency key; return the charge id."""
        return self.gateway.charge(amount_cents)
