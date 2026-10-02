"""A small shop backend. Build one with `Shop(gateway, clock)`."""
from .api import Api
from .auth import Users
from .catalog import Catalog
from .events import EventLog
from .giftcards import GiftCards
from .inventory import Inventory
from .orders import Orders
from .payments import Payments


class Shop:
    def __init__(self, gateway, clock):
        self.events = EventLog(clock)
        self.catalog = Catalog(self.events)
        self.inventory = Inventory(self.events)
        self.payments = Payments(gateway, self.events)
        self.giftcards = GiftCards(self.events)
        self.orders = Orders(self.catalog, self.inventory, self.payments, self.events,
                             self.giftcards)
        self.users = Users(self.events)
        self.api = Api(self)
