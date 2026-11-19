"""Trade-show booth sign-up."""


def booth_signup(shop, username: str, pin: str) -> dict:
    """Create a customer and return its principal (as Users.login returns it).

    Booth accounts get the same password policy as every other account: Users.create enforces
    the 12-character minimum, since a 4-digit PIN can be guessed in at most 10,000 tries.
    """
    shop.users.create(username, pin, "customer", "%s@booth.invalid" % username)
    return {"username": username, "role": "customer"}
