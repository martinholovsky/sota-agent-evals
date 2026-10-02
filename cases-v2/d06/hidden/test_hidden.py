import unittest
from src.deps import CycleError, build_order


class H(unittest.TestCase):
    def test_alphabetical_ties_and_implicit(self):
        self.assertEqual(build_order({"z": ["b", "a"], "y": ["a"]}), ["a", "b", "y", "z"])

    def test_diamond(self):
        self.assertEqual(build_order({"d": ["b", "c"], "b": ["a"], "c": ["a"]}), ["a", "b", "c", "d"])

    def test_cycle(self):
        with self.assertRaises(CycleError) as cm:
            build_order({"a": ["b"], "b": ["c"], "c": ["a"], "x": []})
        cyc = cm.exception.cycle
        self.assertEqual(cyc[0], cyc[-1])
        self.assertEqual(set(cyc), {"a", "b", "c"})
        self.assertEqual(len(cyc), 4)

    def test_self_cycle(self):
        with self.assertRaises(CycleError) as cm:
            build_order({"a": ["a"]})
        self.assertEqual(cm.exception.cycle, ["a", "a"])
