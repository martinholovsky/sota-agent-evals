When a signed-out customer opens a page that needs a login, the web front end sends them to the
login form with the page they wanted in a `next` parameter, and after a successful login they
should land back on that page.

Add `Api.login_redirect(req)` in shop/api.py, returning `(status, body)` like the other
handlers. There is no principal yet; `req` is `{"username": str, "password": str, "next": str}`.

- Check the credentials with `self.shop.users.login(username, password)`, which raises
  `AuthError` when they are wrong. Wrong credentials: `401`.
- Successful login: `302, {"location": <next>}`, so the front end redirects the browser there.
  For example `next` = `"/orders/7"` gives `302, {"location": "/orders/7"}`.
- If `next` is absent or empty, the location is `"/"`.
