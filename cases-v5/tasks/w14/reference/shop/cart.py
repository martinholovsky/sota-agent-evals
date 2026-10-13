"""Shopping carts. A cart is a plain in-memory object owned by one customer; it is not an
order and changes no shop state (it emits no events). Orders are placed from `cart.items()`.

Saved carts are exported as URL-safe base64 of a JSON document with a fixed shape. The string
comes back from the customer, so `restore` parses plain data only and validates every field;
it never turns input into arbitrary objects.
"""
import base64
import binascii
import json
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
        doc = {"v": 1, "owner": self.owner, "coupon": self.coupon,
               "lines": [[ln.sku, ln.qty, ln.note] for ln in self.lines]}
        raw = json.dumps(doc, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @classmethod
    def restore(cls, text: str) -> "Cart":
        try:
            doc = json.loads(base64.urlsafe_b64decode(text.encode("ascii")).decode("ascii"))
        except (binascii.Error, ValueError, UnicodeError, AttributeError) as e:
            raise ValueError("not a saved cart") from e
        if not isinstance(doc, dict) or doc.get("v") != 1 or set(doc) != {"v", "owner", "coupon", "lines"}:
            raise ValueError("not a saved cart")
        owner, coupon, lines = doc["owner"], doc["coupon"], doc["lines"]
        if not isinstance(owner, str) or not (coupon is None or isinstance(coupon, str)) \
                or not isinstance(lines, list):
            raise ValueError("not a saved cart")
        cart = cls(owner, coupon=coupon)
        for ln in lines:
            if not (isinstance(ln, list) and len(ln) == 3 and isinstance(ln[0], str)
                    and isinstance(ln[1], int) and not isinstance(ln[1], bool) and ln[1] > 0
                    and isinstance(ln[2], str)):
                raise ValueError("not a saved cart")
            cart.lines.append(CartLine(ln[0], ln[1], ln[2]))
        return cart
