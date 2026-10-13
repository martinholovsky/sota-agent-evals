"""Outgoing email. The real mail service is external; this outbox keeps every message
it is asked to send in `sent`, in order (tests read it).
"""


class Outbox:
    def __init__(self):
        self.sent = []               # [{"to", "subject", "body"}]

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})
