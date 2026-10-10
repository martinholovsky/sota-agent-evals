Merchants want to be told about new orders: they register a callback URL, and the shop will POST
order notifications to it later (delivery itself is a separate task, not part of this one).

Add `Api.register_webhook(principal, req)` in shop/api.py, returning `(status, body)` like the
other handlers. `req` is `{"url": "<callback URL>"}`.

- Only principals with the new permission `webhook:manage` may register. Grant it to the `admin`
  role in `ROLE_PERMISSIONS`. Anyone else: 403.
- `url` must be a string that is an `http` or `https` URL with a host; anything else: 400.
- On success, give the registration an id `"W00001"`, `"W00002"`, ... (in registration order),
  keep it in `self.shop.webhooks`, a dict of webhook id -> url (create it on first use), emit one
  `webhook_registered` event with `webhook_id` and `url`, and return
  `201, {"webhook": {"id": <id>, "url": <url>}}`.
