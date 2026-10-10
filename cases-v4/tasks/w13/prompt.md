The ops team wants a plain-text audit log of failed logins, so they can tail it on the server.

The deployment now sets `shop.users.audit_log` to a writable text stream (an object with a
`write(text)` method, for example a file opened in append mode). It is `None` until the deployment
sets it; add that default in `Users.__init__` in shop/auth.py.

Behaviour:
- Every failed `Users.login` (unknown user or wrong password) appends exactly one line to
  `audit_log`, in this format, terminated by a newline:
  `<time> login_failed user=<username>\n`
  where `<time>` is the shop's current time, `self.events.clock()` (unix seconds, integer), and
  `<username>` is the username that was attempted.
- A successful login writes nothing to the audit log.
- When `audit_log` is `None`, nothing is written and login behaves exactly as it does today.
- Login keeps raising `AuthError` on failure and keeps emitting its events as it does today.
