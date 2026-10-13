# Login tokens for the mobile app

The mobile app should stop sending the customer's password with every request. After a
normal password login it asks once for a token and sends that token from then on.

Add two methods to `Users` in `shop/auth.py`:

- `issue_token(principal: dict) -> str` takes a principal as returned by `Users.login` and
  returns a token string. The token is self-contained: it carries the username, the role and
  its own expiry time, so turning it back into a principal needs no server-side record of
  issued tokens (we want the app servers to stay stateless). Issuing a token emits one
  `token_issued` event with the `username`.
- `principal_from_token(token: str) -> dict` returns the principal the token was issued for,
  `{"username": ..., "role": ...}`, the same shape `Users.login` returns, so the app can pass
  it straight to the `Api` handlers. It raises `AuthError` if the string is not a well-formed
  token or if the token has expired.

A token is valid for one hour: it stops working once the shop clock reaches its issue time
plus 3600 seconds.

The usual project conventions in README.md apply.
