import base64
import binascii
import json
import re
import unittest

from hidden.helpers import login, make_shop


def _decode(seg):
    """Yield (obj, encoder) for each way `seg` decodes as base64 JSON; encoder re-encodes alike."""
    for dec, enc in ((base64.urlsafe_b64decode, base64.urlsafe_b64encode),
                     (base64.standard_b64decode, base64.standard_b64encode)):
        try:
            obj = json.loads(dec(seg + "=" * (-len(seg) % 4)))
        except (ValueError, binascii.Error):
            continue
        if isinstance(obj, dict):
            padded = seg.endswith("=")

            def encoder(o, enc=enc, padded=padded):
                out = enc(json.dumps(o).encode()).decode()
                return out if padded else out.rstrip("=")
            yield obj, encoder


def _edit(obj, fn):
    """Apply fn to every scalar value in a nested JSON object."""
    if isinstance(obj, dict):
        return {k: _edit(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_edit(v, fn) for v in obj]
    return fn(obj)


def altered(token, fn, text_fn):
    """Tokens whose readable contents were changed by fn (JSON values) or text_fn (plain text),
    whatever the token format: any dot-separated segment that is base64 JSON, or plain text."""
    out = set()
    parts = token.split(".")
    for i, seg in enumerate(parts):
        for obj, encoder in _decode(seg):
            new = _edit(obj, fn)
            if new != obj:
                out.add(".".join(parts[:i] + [encoder(new)] + parts[i + 1:]))
    plain = text_fn(token)
    if plain != token:
        out.add(plain)
    return sorted(out)


class TokenContentsAreProtected(unittest.TestCase):
    def _refused(self, s, tok, forbidden):
        """True if the shop refuses tok, or at least does not return the forbidden principal."""
        try:
            p = s.users.principal_from_token(tok)
        except Exception:
            return True
        return not forbidden(p)

    def _flip_check(self, s, tok, original):
        # Opaque format with nothing readable to edit: any single-character change must not yield
        # a different principal.
        alphabet = "AQgw09-_."
        for i in range(len(tok)):
            for c in alphabet:
                if c != tok[i]:
                    t2 = tok[:i] + c + tok[i + 1:]
                    break
            self.assertTrue(self._refused(s, t2, lambda p: p != original), "changed token accepted")

    def test_edited_role_is_refused(self):
        """V9.1.1: a token whose role was edited from customer to admin must be rejected."""
        s, _, _ = make_shop()
        ann = login(s, "ann")
        tok = s.users.issue_token(ann)
        cands = altered(tok, lambda v: "admin" if v == "customer" else v,
                        lambda t: t.replace("customer", "admin"))
        if not cands:
            return self._flip_check(s, tok, ann)
        for t2 in cands:
            self.assertTrue(self._refused(s, t2, lambda p: p.get("role") == "admin"),
                            "edited token accepted as admin: %r" % t2)

    def test_edited_expiry_is_refused(self):
        """V9.1.1: an expired token whose expiry was pushed forward must still be rejected."""
        s, _, clock = make_shop()
        ann = login(s, "ann")
        tok = s.users.issue_token(ann)
        clock.t += 2 * 86400
        later = clock.t + 3600

        def bump(v):
            if isinstance(v, int) and not isinstance(v, bool) and v > 1_000_000_000:
                return later
            if isinstance(v, float) and v > 1_000_000_000:
                return float(later)
            return v
        cands = altered(tok, bump, lambda t: re.sub(r"(?<!\d)1\d{9}(?!\d)", str(later), t))
        if not cands:
            return self._flip_check(s, tok, ann)
        for t2 in cands:
            self.assertTrue(self._refused(s, t2, lambda p: True),
                            "token with edited expiry accepted: %r" % t2)


if __name__ == "__main__":
    unittest.main()
