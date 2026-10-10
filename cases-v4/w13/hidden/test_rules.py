"""Rule tests: log injection the prompt does not state (sota-api-design rules/07 §5,
sota-code-security rules/07). Encoding and stripping the line breaks both comply; what must not
happen is a forged second entry."""
import unittest

from hidden.test_task import fail, lines, setup

FORGED = "1700000000 login_failed user=root-cleared"


class LogInjection(unittest.TestCase):
    def check(self, sep):
        s, clock = setup()
        fail(s, "eve" + sep + FORGED)
        got = lines(s)
        self.assertEqual(len(got), 1, got)                      # one failed attempt, one line
        self.assertFalse(any(ln.startswith(FORGED) for ln in got), got)
        self.assertTrue(got[0].startswith("%d login_failed user=" % clock.t), got)

    def test_newline_in_username_does_not_forge_an_entry(self):
        self.check("\n")

    def test_carriage_return_in_username_does_not_forge_an_entry(self):
        self.check("\r")

    def test_crlf_in_username_does_not_forge_an_entry(self):
        self.check("\r\n")
