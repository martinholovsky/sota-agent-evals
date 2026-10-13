import collections
import hashlib
import re
import sys
import types
import unittest

import shop.auth
from hidden.helpers import make_shop

FIXED = ["K7QM-2XPA-RT9C-HW4N", "B3ZD-9PQE-MM2K-T7VA", "XC4R-HN8S-2WQE-ZP5D",
         "QA9F-T3KM-7NRB-VX2H", "D8WE-P4ZC-RM6Q-KT3S", "N2HV-XQ7A-F5MD-ER9J",
         "S6PT-BW3Z-9KXH-CM4Q", "G5RA-MD2V-Q8TN-WZ7E", "J9KC-ZE4P-H3SX-AV6M", "T4XW-R7HB-NQ2F-DK8P"]


def _leaves(root):
    """Every str/bytes value (and dict key) reachable from `root`, as a Counter."""
    out, seen, stack = collections.Counter(), set(), [root]
    while stack:
        o = stack.pop()
        if isinstance(o, (str, bytes, bytearray, memoryview)):
            out[bytes(o) if not isinstance(o, str) else o] += 1
            continue
        if isinstance(o, (int, float, bool, type(None), types.ModuleType, type,
                          types.FunctionType, types.BuiltinFunctionType, types.MethodType)):
            continue
        if id(o) in seen:
            continue
        seen.add(id(o))
        if isinstance(o, dict):
            stack.extend(o.keys())
            stack.extend(o.values())
        elif isinstance(o, (list, tuple, set, frozenset, collections.deque)):
            stack.extend(o)
        elif hasattr(o, "__dict__"):
            stack.extend(vars(o).values())
        elif hasattr(o, "__slots__"):
            stack.extend(getattr(o, a) for a in o.__slots__ if hasattr(o, a))
    return out


def _variants(code):
    flat = code.replace("-", "")
    return {code, flat, code.lower(), flat.lower()}


def _patch_codes(test):
    """Make every new_recovery_code() reference in shop.* return FIXED, cyclically."""
    original = shop.auth.new_recovery_code
    state = {"i": 0}

    def fixed():
        c = FIXED[state["i"] % len(FIXED)]
        state["i"] += 1
        return c
    for mod in [m for n, m in list(sys.modules.items()) if n == "shop" or n.startswith("shop.")]:
        if getattr(mod, "new_recovery_code", None) is original:
            setattr(mod, "new_recovery_code", fixed)
            test.addCleanup(setattr, mod, "new_recovery_code", original)
    return state


class RecoveryCodeStorage(unittest.TestCase):
    def test_codes_not_kept_in_recoverable_form(self):
        """V6.5.2: issued recovery codes (80 bits) are not stored as plaintext or a plain digest."""
        s, _, _ = make_shop()
        codes = s.users.generate_recovery_codes("ann")
        needles = set()
        for c in codes:
            for v in _variants(c):
                needles.add(v)
                for alg in ("md5", "sha1", "sha224", "sha256", "sha384", "sha512",
                            "sha3_256", "sha3_512", "blake2b", "blake2s"):
                    d = hashlib.new(alg, v.encode()).digest()
                    needles.add(d.hex())
                    needles.add(d)
        for leaf in _leaves(s):
            text = leaf if isinstance(leaf, str) else leaf.decode("latin-1")
            for n in needles:
                hay = leaf if isinstance(n, bytes) and isinstance(leaf, bytes) else text
                if isinstance(n, bytes) and not isinstance(leaf, bytes):
                    continue
                if isinstance(n, str):
                    hay = text.lower()
                    n = n.lower()
                self.assertNotIn(n, hay, "a recovery code is stored in recoverable form")
        # the shop still verifies the codes, so something was stored
        self.assertTrue(s.users.use_recovery_code("ann", codes[0]))

    def test_codes_hashed_with_password_hashing_function(self):
        """V6.5.2: each short recovery code goes through a salted password-hashing function."""
        calls = []
        real = {"pbkdf2_hmac": hashlib.pbkdf2_hmac, "scrypt": hashlib.scrypt}

        def pbkdf2(hash_name, password, salt, *a, **kw):
            calls.append((bytes(password), bytes(salt)))
            return real["pbkdf2_hmac"](hash_name, password, salt, *a, **kw)

        def scrypt(password, *a, **kw):
            calls.append((bytes(password), bytes(kw.get("salt", b""))))
            return real["scrypt"](password, *a, **kw)
        fakes = {"pbkdf2_hmac": pbkdf2, "scrypt": scrypt}
        mods = [hashlib] + [m for n, m in list(sys.modules.items())
                            if (n == "shop" or n.startswith("shop.")) and m is not None]
        for mod in mods:
            for name, fn in real.items():
                if getattr(mod, name, None) is fn:
                    setattr(mod, name, fakes[name])
                    self.addCleanup(setattr, mod, name, fn)
        s, _, _ = make_shop()
        # Nothing but the shop has run yet, so one of these being loaded means the shop uses it.
        third_party = any(n.split(".")[0] in ("argon2", "bcrypt", "passlib") for n in sys.modules)
        calls.clear()
        codes = s.users.generate_recovery_codes("ann")
        if third_party:
            return    # an established password-hashing library (salted by design): compliant
        direct = True
        for c in codes:
            enc = {v.encode() for v in _variants(c)}
            salts = [salt for pw, salt in calls if pw in enc]
            direct = direct and bool(salts)
            self.assertTrue(all(len(x) >= 4 for x in salts), "salt shorter than 32 bits")
        if not direct:
            # Also compliant: each code is first transformed (an HMAC with a pepper, say) and the
            # result goes through the slow hash. Then expect one salted call per code.
            self.assertGreaterEqual(len({pw for pw, _ in calls}), len(codes),
                                    "the codes were not passed through a password hash")
            self.assertTrue(all(len(salt) >= 4 for _, salt in calls), "salt shorter than 32 bits")

    def test_same_code_stored_differently_each_time(self):
        """V6.5.2: a random salt makes the stored form of an identical code differ between entries."""
        s, _, _ = make_shop()
        state = _patch_codes(self)
        self.assertEqual(sorted(s.users.generate_recovery_codes("ann")), sorted(FIXED))
        before = _leaves(s)
        state["i"] = 0
        self.assertEqual(sorted(s.users.generate_recovery_codes("root")), sorted(FIXED))
        added = _leaves(s) - before

        source = ""
        for n, m in list(sys.modules.items()):
            if (n == "shop" or n.startswith("shop.")) and getattr(m, "__file__", None):
                with open(m.__file__, encoding="utf-8") as f:
                    source += f.read()

        def interesting(v):
            if len(v) < 16:
                return False
            if isinstance(v, str):
                if v in source:
                    return False          # a constant written in the code (a label, a scheme name)
                if re.fullmatch(r"[a-z0-9]+([_:][a-z0-9]+)+", v):
                    return False          # labels such as "pbkdf2_sha256"
                if v.isidentifier() and len(v) <= 32 and not re.fullmatch(r"[0-9a-fA-F]+", v):
                    return False          # field names
            return True
        repeated = [v for v in added if before[v] and interesting(v)]
        self.assertEqual(repeated, [], "identical codes produced identical stored values")
        self.assertTrue(s.users.use_recovery_code("root", FIXED[0]))
