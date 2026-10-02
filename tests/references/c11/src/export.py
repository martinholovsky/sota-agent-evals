import csv
import io

DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def _cell(v):
    if isinstance(v, str) and v.startswith(DANGEROUS):
        return "'" + v
    return v


def to_csv(rows: list) -> str:
    buf = io.StringIO()
    csv.writer(buf).writerows([[_cell(v) for v in r] for r in rows])
    return buf.getvalue()
