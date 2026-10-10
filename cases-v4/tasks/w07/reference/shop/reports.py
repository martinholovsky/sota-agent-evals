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


_FORMULA_START = ("=", "+", "-", "@", "\t", "\r", "\x00")


def _cell(value: str) -> str:
    """Neutralise spreadsheet formula triggers (sota-code-security rules/01, CSV injection)."""
    return "'" + value if value.startswith(_FORMULA_START) else value


def products_csv(catalog) -> str:
    """One row per active product: sku, name, price (formatted). Every field quoted."""
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(["sku", "name", "price"])
    for p in catalog.listing():
        w.writerow([_cell(p["sku"]), _cell(p["name"]), fmt(p["price"])])
    return buf.getvalue()
