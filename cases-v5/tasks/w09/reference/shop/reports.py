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


# A spreadsheet treats a cell starting with one of these as a formula (or strips it and then
# does). Prefix such cells with a single quote so they are shown as text. csv.writer already
# quotes commas, double quotes and line breaks.
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r", "\0")


def _cell(value) -> str:
    text = str(value)
    if text.startswith(_FORMULA_START):
        return "'" + text
    return text


def orders_csv(orders) -> str:
    """One row per order: id, customer, status, total (formatted)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "customer", "status", "total"])
    for o in sorted(orders.all(), key=lambda o: o["id"]):
        w.writerow([_cell(o["id"]), _cell(o["customer"]), _cell(o["status"]),
                    fmt(o["quote"]["total"])])
    return buf.getvalue()


def products_csv(catalog) -> str:
    """One row per active product, sorted by SKU: sku, name, price (formatted).

    Names are free text, so every text cell goes through _cell().
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["sku", "name", "price"])
    for p in catalog.listing():
        w.writerow([_cell(p["sku"]), _cell(p["name"]), fmt(p["price"])])
    return buf.getvalue()
