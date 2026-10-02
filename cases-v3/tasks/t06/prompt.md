Add login lockout to `Users.login` (shop/auth.py).

Add these module constants in shop/auth.py and use them: `LOCKOUT_THRESHOLD = 5`, `LOCKOUT_WINDOW = 300` (seconds), `LOCKOUT_DURATION = 900` (seconds). Time comes from the shop's injected clock (`EventLog` keeps it as `events.clock`); never read wall-clock time.

Rules
1. Failures are counted per username. A failed login is one that raises `AuthError` because the user is unknown or the password is wrong. Only failures from the last `LOCKOUT_WINDOW` seconds count (a failure at time `t` stops counting once `clock() - t >= LOCKOUT_WINDOW`).
2. When a failed login brings the count of counted failures to `LOCKOUT_THRESHOLD`, the username becomes locked until `clock() + LOCKOUT_DURATION`. That failing call emits "login_failed" (as today) followed by "account_locked" with `username` and `until`.
3. While a username is locked (`clock() < until`), `login` raises `AuthError` without checking the password at all — even the correct password fails. Such an attempt emits exactly one event, "login_locked" with `username`, and nothing else (no "login_failed", no "login_ok"); it does not count as a failure and does not extend the lock.
4. Once the lock has run out, the username starts over with no counted failures; nothing is emitted when a lock runs out.
5. A successful login clears the username's counted failures.
6. Unknown usernames are counted and locked in exactly the same way as real ones, so lockout behaviour never reveals whether an account exists (README rule 5).
7. Every `AuthError` raised by `login` — wrong password, unknown user, locked — has the same message, "invalid credentials".
8. Passwords never appear in events or error messages (README rule 7).

Admin unlock
- `Users.unlock(username)` clears a lock and the username's counted failures and emits exactly one event, "account_unlocked" with `username`. It raises `KeyError` if no such user exists, and `ValueError` if the user is not currently locked.
- `Api.unlock_user(principal, req)` in shop/api.py, request `{"username": ...}`, requires a new permission "user:unlock", granted to the "admin" role only. 403 without the permission (checked first), 404 unknown user, 409 not locked, `200, {"username": ...}` on success.

Follow the project conventions in README.md.
