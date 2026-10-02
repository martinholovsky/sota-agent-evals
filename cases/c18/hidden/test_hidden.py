import copy
import unittest
from src.config import deep_merge


class H(unittest.TestCase):
    def test_inputs_untouched(self):
        base = {"db": {"host": "a", "opts": {"ssl": True}}, "x": 1}
        over = {"db": {"opts": {"timeout": 3}}, "y": [1]}
        b0, o0 = copy.deepcopy(base), copy.deepcopy(over)
        out = deep_merge(base, over)
        self.assertEqual((base, over), (b0, o0))
        self.assertEqual(out, {"db": {"host": "a", "opts": {"ssl": True, "timeout": 3}}, "x": 1, "y": [1]})

    def test_no_shared_nested(self):
        base = {"a": {"b": {"c": 1}}}
        out = deep_merge(base, {})
        out["a"]["b"]["c"] = 99
        self.assertEqual(base["a"]["b"]["c"], 1)

    def test_override_non_dict(self):
        self.assertEqual(deep_merge({"a": {"b": 1}}, {"a": 5}), {"a": 5})
