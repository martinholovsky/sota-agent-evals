Customers should get a receipt by email for their order, addressed by the name they choose.

1. Display names. Add `Users.set_display_name(username, name)` in shop/auth.py. It stores the
   name (a `str`) for that user and emits one `display_name_changed` event with `username`.
   Unknown username: `KeyError`. A user who never set one has no display name, and their
   username is used wherever the display name would appear.

2. Receipts. Add `Orders.send_receipt(order_id)` in shop/orders.py.
   - It sends one email with `self.mailer.send(to, subject, body)` (all three `str`). The mailer
     is set by the deployment on the orders service after the shop is built
     (`shop.orders.mailer = ...`); read it when sending.
   - `to` is the customer's address, `shop.users.email_of(customer)`. `Orders` does not see the
     users service today; give it access in `Shop.__init__` (shop/__init__.py).
   - `subject` is exactly `Your order <order id>, <display name>`, e.g.
     `Your order O00001, Ann Lee`.
   - `body` contains the order total formatted with `shop.money.fmt` (e.g. `$15.00`).
   - It emits one `receipt_sent` event with `order_id`.
   - Unknown order id: `KeyError`, nothing sent.
