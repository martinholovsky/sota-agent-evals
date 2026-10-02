class PaymentService:
    def __init__(self, gateway):
        self.gateway = gateway
        self._done = {}

    def charge(self, idempotency_key: str, amount_cents: int) -> str:
        if idempotency_key in self._done:
            amount, cid = self._done[idempotency_key]
            if amount != amount_cents:
                raise ValueError("idempotency key reused with a different amount")
            return cid
        cid = self.gateway.charge(amount_cents)
        self._done[idempotency_key] = (amount_cents, cid)
        return cid
