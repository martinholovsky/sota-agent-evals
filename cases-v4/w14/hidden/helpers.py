from shop import Shop
from shop.payments import GatewayError


class Clock:
    def __init__(self, t=1_700_000_000):
        self.t = t

    def __call__(self):
        return self.t


class FakeGateway:
    def __init__(self, fail_charge=False):
        self.fail_charge = fail_charge
        self.charges = {}            # charge_id -> amount
        self.refunds = []            # (charge_id, amount)

    def charge(self, amount, token):
        if self.fail_charge or token == "tok_declined":
            raise GatewayError("declined")
        cid = "ch_%d" % (len(self.charges) + 1)
        self.charges[cid] = amount
        return cid

    def refund(self, charge_id, amount):
        if charge_id not in self.charges:
            raise GatewayError("no such charge")
        if sum(a for c, a in self.refunds if c == charge_id) + amount > self.charges[charge_id]:
            raise GatewayError("refund exceeds charge")
        self.refunds.append((charge_id, amount))
        return "re_%d" % len(self.refunds)


def make_shop(**gw):
    gateway, clock = FakeGateway(**gw), Clock()
    s = Shop(gateway, clock)
    s.catalog.add("TEA-1", "Green tea", 1250)
    s.catalog.add("MUG-1", "Mug", 800)
    s.inventory.receive("TEA-1", 10)
    s.inventory.receive("MUG-1", 5)
    s.users.create("ann", "correct horse battery", "customer", "ann@example.com")
    s.users.create("root", "correct horse staple!", "admin", "root@example.com")
    return s, gateway, clock


def login(s, who):
    pw = {"ann": "correct horse battery", "root": "correct horse staple!"}[who]
    return s.users.login(who, pw)
