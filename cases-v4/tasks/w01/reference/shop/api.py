import hashlib
import hmac
import json

"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError


class Api:
    def __init__(self, shop):
        self.shop = shop

    def place_order(self, principal, req: dict):
        try:
            require(principal, "order:place")
        except AuthError as e:
            return 403, {"error": str(e)}
        items, token = req.get("items"), req.get("token")
        if not isinstance(items, dict) or not isinstance(token, str):
            return 400, {"error": "items (object) and token (string) required"}
        try:
            order = self.shop.orders.place(principal["username"], items, token, req.get("coupon"))
        except (OrderError, ValueError) as e:
            return 400, {"error": str(e)}
        except KeyError as e:
            return 404, {"error": "unknown sku: %s" % e.args[0]}
        except OutOfStock as e:
            return 409, {"error": "out of stock: %s" % e.args[0]}
        return 201, {"order": order}

    def get_order(self, principal, req: dict):
        oid = req.get("id")
        try:
            order = self.shop.orders.get(oid)
        except KeyError:
            return 404, {"error": "no such order"}
        own = order["customer"] == principal["username"]
        try:
            require(principal, "order:view_own" if own else "order:view_any")
        except AuthError:
            return 404, {"error": "no such order"}       # do not reveal existence
        return 200, {"order": order}

    def cancel_order(self, principal, req: dict):
        try:
            require(principal, "order:cancel")
        except AuthError as e:
            return 403, {"error": str(e)}
        try:
            return 200, {"order": self.shop.orders.cancel(req.get("id"))}
        except KeyError:
            return 404, {"error": "no such order"}
        except OrderError as e:
            return 409, {"error": str(e)}

    TOLERANCE_S = 300                       # replay window: +-5 min (sota-api-design rules/06)

    def payment_webhook(self, raw_body, headers):
        ts, sig = headers.get("x-timestamp"), headers.get("x-signature")
        if not ts or not sig:
            return 401, {"error": "unsigned"}
        try:
            sent = int(ts)
        except ValueError:
            return 401, {"error": "bad timestamp"}
        if abs(self.shop.events.clock() - sent) > self.TOLERANCE_S:
            return 401, {"error": "stale or future timestamp"}
        mac = hmac.new(self.shop.webhook_secret, ts.encode() + b"." + raw_body, hashlib.sha256)
        if not hmac.compare_digest(mac.hexdigest(), sig):
            return 401, {"error": "bad signature"}
        event = json.loads(raw_body)
        seen = self.__dict__.setdefault("_seen_event_ids", set())
        if event.get("id") in seen:
            return 200, {"ok": True}            # duplicate delivery: no-op
        if event.get("type") != "charge.disputed":
            seen.add(event.get("id"))
            return 200, {"ok": True}
        result = self._apply_dispute(event)
        if result[0] == 200:
            seen.add(event.get("id"))
        return result

    def _find_by_charge(self, charge_id):
        for o in self.shop.orders.all():
            if o["charge_id"] == charge_id:
                return o
        return None

    def _apply_dispute(self, event):
        o = self._find_by_charge((event.get("data") or {}).get("charge_id"))
        if o is None:
            return 404, {"error": "no such charge"}
        self.shop.orders._orders[o["id"]]["status"] = "disputed"
        self.shop.events.emit("order_disputed", order_id=o["id"], charge_id=o["charge_id"])
        return 200, {"ok": True}
