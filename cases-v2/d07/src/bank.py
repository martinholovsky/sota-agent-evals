class InsufficientFunds(Exception):
    pass


class Bank:
    def __init__(self, balances: dict):
        self.balances = dict(balances)   # account -> cents
        self.ledger = []                 # (from, to, cents, reference)

    def transfer(self, src: str, dst: str, cents: int, reference: str) -> bool:
        """Move cents from src to dst.
        - cents must be a positive int; src and dst must exist and differ; else ValueError.
        - If src would go below 0, raise InsufficientFunds and change NOTHING.
        - `reference` makes the call idempotent: a repeat with the same reference and the
          same (src, dst, cents) does nothing and returns False; the same reference with
          different arguments raises ValueError.
        - On success append (src, dst, cents, reference) to the ledger and return True."""
        raise NotImplementedError
