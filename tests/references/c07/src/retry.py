import random
import time


def retry(fn, attempts=3, base=0.1, cap=2.0, retry_on=(Exception,), sleep=time.sleep, rand=random.random):
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    for i in range(attempts):
        try:
            return fn()
        except retry_on:
            if i == attempts - 1:
                raise
            sleep(rand() * min(cap, base * 2 ** i))
