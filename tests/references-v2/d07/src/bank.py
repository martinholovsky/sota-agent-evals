class InsufficientFunds(Exception):
    pass


class Bank:
    def __init__(self, balances: dict):
        self.balances = dict(balances)
        self.ledger = []
        self._refs = {}

    def transfer(self, src: str, dst: str, cents: int, reference: str) -> bool:
        if not isinstance(cents, int) or isinstance(cents, bool) or cents <= 0:
            raise ValueError("cents must be a positive int")
        if src not in self.balances or dst not in self.balances or src == dst:
            raise ValueError("bad accounts")
        if reference in self._refs:
            if self._refs[reference] != (src, dst, cents):
                raise ValueError("reference reused with different arguments")
            return False
        if self.balances[src] - cents < 0:
            raise InsufficientFunds(src)
        self.balances[src] -= cents
        self.balances[dst] += cents
        self._refs[reference] = (src, dst, cents)
        self.ledger.append((src, dst, cents, reference))
        return True
