"""Payment gateway client. The real gateway is external; tests inject a fake.

gateway.charge(amount_cents, token, idempotency_key=None) -> charge_id   (raises GatewayError)
    idempotency_key: optional string, at most 255 characters. When a charge with the same key
    was already made, the gateway returns that charge's id and does not create a new charge.
gateway.refund(charge_id, amount_cents) -> refund_id  (raises GatewayError)
"""


class GatewayError(Exception):
    pass


class TransientGatewayError(GatewayError):
    """A timeout or brief outage; the charge may or may not have gone through."""


class Payments:
    MAX_ATTEMPTS = 3

    def __init__(self, gateway, events):
        self.gateway = gateway
        self.events = events

    def charge(self, order_id: str, amount: int, token: str) -> str:
        cid = self.gateway.charge(amount, token)
        self.events.emit("payment_captured", order_id=order_id, charge_id=cid, amount=amount)
        return cid

    def refund(self, order_id: str, charge_id: str, amount: int) -> str:
        rid = self.gateway.refund(charge_id, amount)
        self.events.emit("payment_refunded", order_id=order_id, refund_id=rid, amount=amount)
        return rid

    def charge_with_retry(self, order_id: str, amount: int, token: str) -> str:
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                cid = self.gateway.charge(amount, token)
                break
            except TransientGatewayError:
                if attempt == self.MAX_ATTEMPTS:
                    raise
        self.events.emit("payment_captured", order_id=order_id, charge_id=cid, amount=amount)
        return cid
