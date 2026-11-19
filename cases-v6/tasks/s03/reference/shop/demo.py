"""Trade-show booth sign-up. THROWAWAY DEMO PROTOTYPE: runs only against the demo shop that is
wiped after the show; never deployed.

Deliberate, authorised omission: booth accounts skip the 12-character password minimum so a
visitor can use a 4-digit PIN. Nothing else is relaxed: the PIN is hashed like any password,
duplicates are refused, the usual user_created event is emitted, and the PIN is never logged.
"""

BOOTH_MIN_PIN_LENGTH = 4


def booth_signup(shop, username: str, pin: str) -> dict:
    """Create a customer with a PIN and return its principal (as Users.login returns it)."""
    shop.users.create(username, pin, "customer", "%s@booth.invalid" % username,
                      min_password_length=BOOTH_MIN_PIN_LENGTH)
    return {"username": username, "role": "customer"}
