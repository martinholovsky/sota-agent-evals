"""Messages the shop sends to people (e-mail and the like).

The real mail worker drains `messages` and delivers them; tests read `messages` directly.
Each message is a dict: {"to": <address>, "kind": <message type>, **fields}.
Sending is delivery to an external channel, like the payment gateway: it emits no event.
"""


class Outbox:
    def __init__(self):
        self.messages = []

    def send(self, to: str, kind: str, **fields) -> None:
        msg = {"to": to, "kind": kind}
        msg.update(fields)
        self.messages.append(msg)
