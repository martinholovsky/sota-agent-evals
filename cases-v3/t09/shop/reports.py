"""Reports derived from the event log and orders. Reports never change state."""
import csv
import io

from .money import fmt


def sales_summary(orders) -> dict:
    """Totals over all orders, in cents: gross charged, refunded, and net (gross - refunded)."""
    gross = sum(orders.amount_charged(o) for o in orders.all())
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
