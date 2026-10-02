"""Reports derived from the event log and orders. Reports never change state."""
import csv
import io

from .money import fmt


def sales_summary(orders) -> dict:
    """Totals over all orders, in cents: gross charged, refunded, and net (gross - refunded)."""
    gross = sum(o["quote"]["total"] for o in orders.all())
    refunded = sum(o["refunded"] for o in orders.all())
    return {"orders": len(orders.all()), "gross": gross, "refunded": refunded,
            "net": gross - refunded}


def orders_csv(orders) -> str:
    """One row per order: id, customer, status, total (formatted)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "customer", "status", "total"])
    for o in sorted(orders.all(), key=lambda o: o["id"]):
        w.writerow([o["id"], o["customer"], o["status"], fmt(o["quote"]["total"])])
    return buf.getvalue()


EXPORT_HEADER = ["id", "customer", "email", "status", "items", "subtotal", "discount", "tax",
                 "total", "refunded"]
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(text: str) -> str:
    """Neutralise spreadsheet formula injection: prefix a leading formula character with '."""
    return "'" + text if text.startswith(_FORMULA_START) else text


def orders_export_csv(orders, users) -> str:
    """One row per order with customer email, items, the priced quote and refunds.
    Every data cell is protected against spreadsheet formula injection."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(EXPORT_HEADER)
    for o in sorted(orders.all(), key=lambda o: o["id"]):
        try:
            email = users.email_of(o["customer"])
        except KeyError:
            email = ""
        items = ";".join("%s:%d" % (sku, qty) for sku, qty in sorted(o["items"].items()))
        q = o["quote"]
        row = [o["id"], o["customer"], email, o["status"], items, fmt(q["subtotal"]),
               fmt(q["discount"]), fmt(q["tax"]), fmt(q["total"]), fmt(o["refunded"])]
        w.writerow([_safe_cell(str(c)) for c in row])
    return buf.getvalue()
