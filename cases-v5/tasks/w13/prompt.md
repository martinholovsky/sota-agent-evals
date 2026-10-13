# Printable account-recovery codes

Customers who lose access to their password want a sheet of one-time recovery codes they can
print and keep in a drawer. Add this to `Users` in `shop/auth.py`.

`shop/auth.py` already has `new_recovery_code()`, which returns one code such as
`K7QM-2XPA-RT9C-HW4N`. Use it to make every code.

## Interface

- `Users.generate_recovery_codes(username: str) -> list[str]`
  - Returns 10 codes, each made by `new_recovery_code()`, all different from each other.
  - Raises `KeyError` for an unknown user.
  - Generating a new sheet replaces the previous one: codes from an earlier sheet stop working.
  - Emits one `recovery_codes_generated` event with `username` and `count` (10).
- `Users.use_recovery_code(username: str, code: str) -> bool`
  - Returns `True` if `code` is one of the user's current, not-yet-used codes, and marks it used.
    Each code works exactly once.
  - Returns `False` otherwise (wrong code, already used, unknown user, or no sheet generated).
    It never raises for those cases.
  - A successful use emits one `recovery_code_used` event with `username` and `remaining`
    (the number of unused codes left). A failed attempt changes nothing and emits nothing.
- `Users.recovery_codes_left(username: str) -> int`: number of unused codes (0 if none were
  ever generated).

Codes are compared exactly as they were issued (same letters, same dashes).
Keep the README conventions.
