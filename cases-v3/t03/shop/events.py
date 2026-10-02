"""In-process event log. Every state change in the shop emits exactly one event.

Events are dicts: {"type": str, "at": int (clock seconds), **payload}. Consumers
(reports, audit) read `log.events`; never mutate an event after emitting it.
"""


class EventLog:
    def __init__(self, clock):
        self.clock = clock
        self.events = []

    def emit(self, type_: str, **payload) -> dict:
        ev = {"type": type_, "at": self.clock()}
        ev.update(payload)
        self.events.append(ev)
        return ev

    def of_type(self, type_: str) -> list:
        return [e for e in self.events if e["type"] == type_]
