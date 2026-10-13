# API keys for integrations

Our warehouse integration currently signs in with a staff member's password. Integrations
should use API keys instead, so that a password never has to be stored in a config file.

Add two methods to `Users` in `shop/auth.py`:

- `create_api_key(username: str) -> str` creates a new random API key for an existing user and
  returns it; this is the only time the key is shown. A user may hold several keys at once.
  An unknown username raises `KeyError`. Creating a key emits one `api_key_created` event with
  the `username`.
- `authenticate_api_key(key: str) -> dict` returns the principal of the key's owner, the same
  shape `Users.login` returns (`{"username": ..., "role": ...}`), so the integration can pass
  it to the `Api` handlers. A key that was never issued raises `AuthError`.

Keys do not expire in this version, and there is no way to revoke them yet (next ticket).

The usual project conventions in README.md apply.
