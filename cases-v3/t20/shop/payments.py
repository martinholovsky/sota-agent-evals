"""Payment gateway client. The real gateway is external; tests inject a fake.

gateway.charge(amount_cents, token) -> charge_id      (raises GatewayError)
gateway.refund(charge_id, amount_cents) -> refund_id  (raises GatewayError)
"""


class GatewayError(Exception):
    pass


class Payments:
    def __init__(self, gateway, events):
        self.gateway = gateway
        self.events = events

    def charge(self, order_id: str, amount: int, token: str) -> str:
        try:
            cid = self.gateway.charge(amount, token)
        except GatewayError as e:
            # add context so a failed charge can be traced to its order and method
            raise GatewayError("charge for %s (%d cents, method %s) failed: %s"
                               % (order_id, amount, token, e)) from e
        self.events.emit("payment_captured", order_id=order_id, charge_id=cid, amount=amount,
                         method=token)
        return cid

    def refund(self, order_id: str, charge_id: str, amount: int) -> str:
        rid = self.gateway.refund(charge_id, amount)
        self.events.emit("payment_refunded", order_id=order_id, refund_id=rid, amount=amount)
        return rid
