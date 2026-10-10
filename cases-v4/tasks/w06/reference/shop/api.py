"""Request handlers. Each takes a principal (from Users.login) and a plain-dict request,
and returns (status_code, body_dict). Handlers validate input and check permissions;
business rules live in the service modules.
"""
from .auth import AuthError, require
from .inventory import OutOfStock
from .orders import OrderError
from .auth import _hash


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

    # Lockout parameters (sota-code-security rules/02 §1: write them down).
    LOCK_THRESHOLD = 5            # failures per account inside the window before a block
    LOCK_WINDOW_S = 15 * 60       # observation window
    LOCK_BASE_S = 60              # first block; doubles with each further failure
    LOCK_MAX_S = 3600             # cap: a block always lifts
    _DUMMY_SALT = b"\x00" * 16

    def login(self, req: dict):
        username, password = req.get("username"), req.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            return 400, {"error": "username and password (strings) required"}
        now = self.shop.events.clock()
        state = self.__dict__.setdefault("_login_failures", {})
        rec = state.get(username)
        if rec and now - rec["last"] > self.LOCK_WINDOW_S and now >= rec["until"]:
            state.pop(username)
            rec = None
        if rec and now < rec["until"]:
            return 401, {"error": "invalid credentials"}     # blocked: same answer, no check
        if username not in self.shop.users._users:
            _hash(password, self._DUMMY_SALT)                  # similar timing for unknown users
        try:
            principal = self.shop.users.login(username, password)
        except AuthError:
            rec = state.setdefault(username, {"count": 0, "last": now, "until": 0})
            rec["count"] += 1
            rec["last"] = now
            over = rec["count"] - self.LOCK_THRESHOLD
            if over >= 0:
                rec["until"] = now + min(self.LOCK_MAX_S, self.LOCK_BASE_S * 2 ** over)
            return 401, {"error": "invalid credentials"}
        state.pop(username, None)
        return 200, {"principal": principal}
