Bug report from the support and finance teams. Find the root cause and fix it; do not just patch the symptoms.

**1. Cancelling some older orders crashes.** Last week we raised the price of Green tea (TEA-1) from $12.50 to $15.00. Since then, an admin cancelling an order that was placed BEFORE the price change gets a `GatewayError: refund exceeds charge` and the order stays "paid". Orders placed after the change cancel fine.

Reproduction (using the test helpers):

    s, gw, clock = make_shop()
    o = s.orders.place("ann", {"TEA-1": 2}, "tok")      # charged $30.00
    s.catalog.set_price("TEA-1", 1500)
    s.orders.cancel(o["id"])                            # GatewayError: refund exceeds charge

**2. Some customers were refunded less than they paid.** For a different product we LOWERED the price, and cancellations of orders placed before that are "succeeding" but the refund sent to the gateway (and the order's `refunded` field) is smaller than what the customer was charged. Customers are complaining.

**3. The sales summary moves on its own.** `reports.sales_summary` showed a different `gross` this morning than last night although no orders were placed or cancelled overnight; the only change was a catalog price update. Finance needs `gross` to be exactly what customers were charged.

Expected behaviour: whatever happens to catalog prices after an order is placed, cancelling it refunds exactly the amount the customer was charged for it (no more, no less), and reports reflect the amounts actually charged. Everything else must keep working as documented in README.md.
