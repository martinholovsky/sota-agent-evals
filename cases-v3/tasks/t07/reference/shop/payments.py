"""Payment gateway client. The real gateway is external; tests inject a fake.

gateway.charge(amount_cents, token) -> charge_id      (raises GatewayError)
gateway.refund(charge_id, amount_cents) -> refund_id  (raises GatewayError)

Incoming webhooks are signed: HMAC-SHA256(webhook_secret, "<timestamp>.<body>"), lowercase hex.
"""
import hashlib
import hmac

WEBHOOK_TOLERANCE = 300          # seconds, either direction


class GatewayError(Exception):
    pass


class Payments:
    def __init__(self, gateway, events):
        self.gateway = gateway
        self.events = events
        self.webhook_secret = None   # bytes; None = webhooks not configured, all rejected

    def charge(self, order_id: str, amount: int, token: str) -> str:
        cid = self.gateway.charge(amount, token)
        self.events.emit("payment_captured", order_id=order_id, charge_id=cid, amount=amount)
        return cid

    def refund(self, order_id: str, charge_id: str, amount: int) -> str:
        rid = self.gateway.refund(charge_id, amount)
        self.events.emit("payment_refunded", order_id=order_id, refund_id=rid, amount=amount)
        return rid

    def verify_webhook(self, timestamp: str, body: str, signature: str, now: int) -> bool:
        """True iff the timestamp is fresh and the signature matches. Never raises."""
        secret = self.webhook_secret
        if not isinstance(secret, bytes) or not secret:
            return False
        if abs(now - int(timestamp)) > WEBHOOK_TOLERANCE:
            return False
        expected = hmac.new(secret, ("%s.%s" % (timestamp, body)).encode(), hashlib.sha256).hexdigest()
        try:
            given = signature.encode("ascii")
        except UnicodeEncodeError:
            return False
        return hmac.compare_digest(expected.encode("ascii"), given)
