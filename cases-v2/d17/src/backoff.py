def next_delay(attempt: int, retry_after: str | None, now_epoch: float,
               base: float = 0.5, cap: float = 30.0) -> float:
    """Seconds to wait before retry number `attempt` (attempt >= 1).
    - If retry_after is given it wins, but never above `cap`:
        * an integer number of seconds ("120"), or
        * an HTTP-date ("Wed, 21 Oct 2015 07:28:00 GMT"): delay = date - now, min 0.
      A retry_after that is neither raises ValueError.
    - Otherwise exponential: min(cap, base * 2**(attempt-1)).
    - attempt < 1 raises ValueError."""
    raise NotImplementedError
