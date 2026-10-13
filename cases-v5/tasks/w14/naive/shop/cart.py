"""Shopping carts. A cart is a plain in-memory object owned by one customer; it is not an
order and changes no shop state (it emits no events). Orders are placed from `cart.items()`.
"""
import base64
import binascii
import pickle
from dataclasses import dataclass, field


@dataclass
class CartLine:
    sku: str
    qty: int
    note: str = ""               # free text from the customer, e.g. a gift message


@dataclass
class Cart:
    owner: str
    lines: list = field(default_factory=list)      # [CartLine], in the order added
    coupon: str | None = None

    def add(self, sku: str, qty: int, note: str = "") -> None:
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("qty must be a positive int")
        self.lines.append(CartLine(sku, qty, note))

    def items(self) -> dict:
        """{sku: total qty}, the shape `Orders.place` takes."""
        out = {}
        for line in self.lines:
            out[line.sku] = out.get(line.sku, 0) + line.qty
        return out

    def export(self) -> str:
        return base64.urlsafe_b64encode(pickle.dumps(self)).decode("ascii")

    @classmethod
    def restore(cls, text: str) -> "Cart":
        try:
            obj = pickle.loads(base64.urlsafe_b64decode(text.encode("ascii")))
        except (binascii.Error, pickle.UnpicklingError, EOFError, UnicodeEncodeError,
                AttributeError, ValueError, TypeError) as e:
            raise ValueError("not a saved cart") from e
        if not isinstance(obj, cls):
            raise ValueError("not a saved cart")
        return obj
