import pathlib
import shutil
import tempfile
import unittest

from hidden.helpers import login, make_shop
from shop.reports import orders_csv


class Sandbox:
    """A temp root with the reports directory two levels down: <root>/var/shop/reports."""

    def __init__(self):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.reports = self.root / "var" / "shop" / "reports"
        self.reports.mkdir(parents=True)
        (self.root / "outside").mkdir()

    def files(self):
        return sorted(str(p) for p in self.root.rglob("*") if p.is_file())

    def outside_files(self):
        return [f for f in self.files() if not pathlib.Path(f).is_relative_to(self.reports)]

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def setup(testcase):
    s, _, _ = make_shop()
    box = Sandbox()
    testcase.addCleanup(box.close)
    s.reports_dir = str(box.reports)
    s.orders.place("ann", {"TEA-1": 2}, "tok")
    return s, box, login(s, "root")


class Spec(unittest.TestCase):
    def test_saves_csv_under_name(self):
        s, box, root = setup(self)
        status, body = s.api.save_report(root, {"name": "q3-close"})
        self.assertEqual(status, 201)
        f = box.reports / "q3-close.csv"
        self.assertEqual(pathlib.Path(body["path"]).resolve(), f)
        self.assertEqual(f.read_text().splitlines(), orders_csv(s.orders).splitlines())
        evs = s.events.of_type("report_saved")
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["name"], "q3-close")

    def test_same_name_replaces(self):
        s, box, root = setup(self)
        s.api.save_report(root, {"name": "daily"})
        s.orders.place("ann", {"MUG-1": 1}, "tok")
        s.api.save_report(root, {"name": "daily"})
        self.assertEqual((box.reports / "daily.csv").read_text().splitlines(),
                         orders_csv(s.orders).splitlines())
        self.assertEqual(len(box.files()), 1)

    def test_customer_is_403(self):
        s, box, _ = setup(self)
        status, _ = s.api.save_report(login(s, "ann"), {"name": "mine"})
        self.assertEqual(status, 403)
        self.assertEqual(box.files(), [])

    def test_bad_name_is_400(self):
        s, box, root = setup(self)
        for bad in [None, "", 12]:
            self.assertEqual(s.api.save_report(root, {"name": bad})[0], 400, bad)
        self.assertEqual(s.api.save_report(root, {})[0], 400)
        self.assertEqual(box.files(), [])
