V7.3.1 here: once the shop has session tokens, an unused session must lapse after a period of
inactivity so the user has to log in again. The prompt asks for open/principal/close and never
mentions expiry; the natural implementation is a token -> principal dict that lives until
close(), so a token found on a stolen or shared device works forever.
The reference ends a session after 30 idle minutes (documented constant in sessions.py, read
from the shop's clock, `session_expired` event when it lapses).
The rule test advances the shop clock by 24 hours with no use and requires AuthError, then
checks the token stays dead and a fresh login works. Any idle limit up to a day passes, and so
does a solution that only has an absolute lifetime of a day or less (that also forces
re-authentication after the idle period). Spec tests never advance the clock, so no compliant
timeout can break them.
Weakness: the requirement defers the exact limit to the application's own risk analysis; one
day is a deliberately generous ceiling, so the test checks that some inactivity limit exists,
not that it is well chosen.
- Spec reader (2026-10-13): rule test: idle period is now 24 h + 1 s, so an idle limit of exactly one day compared with `>` also passes.
