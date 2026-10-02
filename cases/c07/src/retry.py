import random
import time


def retry(fn, attempts=3, base=0.1, cap=2.0, retry_on=(Exception,), sleep=time.sleep, rand=random.random):
    """Call fn() up to `attempts` times. On an exception in `retry_on`, sleep a full-jitter
    exponential backoff — rand() * min(cap, base * 2**i) for the i-th retry (i from 0) —
    then try again. Return fn()'s result on success; re-raise the LAST exception when the
    attempts are exhausted. Exceptions not in `retry_on` propagate immediately, no sleep.
    attempts < 1 raises ValueError."""
    raise NotImplementedError
