"""Saved carts: dump a cart to a string the client keeps, load it back later."""
import base64
import pickle


class Carts:
    def dump(self, cart: dict) -> str:
        return base64.urlsafe_b64encode(pickle.dumps(cart)).decode("ascii")

    def load(self, s: str) -> dict:
        try:
            cart = pickle.loads(base64.urlsafe_b64decode(s.encode("ascii")))
        except Exception as e:
            raise ValueError("not a saved cart") from e
        if not isinstance(cart, dict):
            raise ValueError("not a saved cart")
        return cart
