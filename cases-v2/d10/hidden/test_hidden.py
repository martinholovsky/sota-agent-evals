import unittest
from src.jdiff import diff


class H(unittest.TestCase):
    def test_nested_sorted(self):
        old = {"b": {"x": 1, "y": 2}, "a": 1, "c": [1, 2]}
        new = {"b": {"x": 1, "z": 3}, "a": 2, "c": [1, 2, 3]}
        self.assertEqual(diff(old, new), [
            {"op": "replace", "path": "/a", "value": 2},
            {"op": "remove", "path": "/b/y"},
            {"op": "add", "path": "/b/z", "value": 3},
            {"op": "replace", "path": "/c", "value": [1, 2, 3]},
        ])

    def test_type_change(self):
        self.assertEqual(diff({"a": {"x": 1}}, {"a": 5}), [{"op": "replace", "path": "/a", "value": 5}])
        self.assertEqual(diff({"a": 1}, {"a": True}), [{"op": "replace", "path": "/a", "value": True}])
        self.assertEqual(diff({"a": 1}, {"a": 1.0}), [{"op": "replace", "path": "/a", "value": 1.0}])

    def test_equal(self):
        self.assertEqual(diff({"a": {"b": [1]}}, {"a": {"b": [1]}}), [])
