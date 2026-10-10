Customers should be able to change their own email address and display name.

Add `Api.update_profile(principal, req)` in shop/api.py, returning `(status, body)` like the other
handlers. It changes the profile of the principal's own user; `req` holds the new values, for
example `{"display_name": "Ann B."}` or `{"email": "ann@new.example", "display_name": "Ann"}`.

An email address must be a string containing `@`, and a display name a non-empty string of at
most 50 characters. A bad value: `400`, and nothing changes. On success return
`200, {"profile": <Users.profile(username) after the change>}`.
