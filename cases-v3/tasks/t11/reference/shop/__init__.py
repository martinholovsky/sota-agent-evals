"""A small shop backend. Build one with `Shop(gateway, clock)`."""
import copy

from .api import Api
from .auth import Users
from .catalog import Catalog
from .events import EventLog
from .inventory import Inventory
from .orders import Orders
from .payments import Payments


class Shop:
    def __init__(self, gateway, clock):
        self.events = EventLog(clock)
        self.catalog = Catalog(self.events)
        self.inventory = Inventory(self.events)
        self.payments = Payments(gateway, self.events)
        self.orders = Orders(self.catalog, self.inventory, self.payments, self.events)
        self.users = Users(self.events)
        self.api = Api(self)

    def export_user_data(self, username: str) -> dict:
        """GDPR access export: the user's account, orders and the events about them."""
        account = self.users.profile(username)          # KeyError for an unknown user
        orders = sorted(self.orders.for_customer(username), key=lambda o: int(o["id"][1:]))
        oids = {o["id"] for o in orders}
        events = [e for e in self.events.events
                  if e.get("username") == username or e.get("customer") == username
                  or e.get("order_id") in oids]
        out = copy.deepcopy({"account": account, "orders": orders, "events": events})
        self.events.emit("user_data_exported", username=username)
        return out
