import io
import os
import pathlib
import shutil
import tempfile
import unittest
import zipfile

from hidden.helpers import make_shop


def make_zip(entries):
    """entries: list of (name, bytes); a name ending in '/' is a directory entry."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            z.writestr(name, data)
    return buf.getvalue()


class Sandbox:
    """A temp root with the image directory two levels down, so a '..' entry has somewhere
    real to land: <root>/site/images."""

    def __init__(self):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.dest = self.root / "site" / "images"
        self.dest.mkdir(parents=True)
        (self.root / "outside").mkdir()

    def files(self):
        return sorted(str(p) for p in self.root.rglob("*") if p.is_file())

    def outside_files(self):
        return [f for f in self.files() if not pathlib.Path(f).is_relative_to(self.dest)]

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


class Spec(unittest.TestCase):
    def setUp(self):
        self.s, _, _ = make_shop()
        self.box = Sandbox()
        self.addCleanup(self.box.close)

    def test_writes_files_and_subfolders(self):
        zb = make_zip([("TEA-1.png", b"tea"), ("mugs/", b""), ("mugs/MUG-1.png", b"mug")])
        names = self.s.catalog.import_images(zb, str(self.box.dest))
        self.assertEqual(names, ["TEA-1.png", "mugs/MUG-1.png"])
        self.assertEqual((self.box.dest / "TEA-1.png").read_bytes(), b"tea")
        self.assertEqual((self.box.dest / "mugs" / "MUG-1.png").read_bytes(), b"mug")
        evs = self.s.events.of_type("images_imported")
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["count"], 2)

    def test_replaces_existing_file(self):
        (self.box.dest / "TEA-1.png").write_bytes(b"old")
        self.s.catalog.import_images(make_zip([("TEA-1.png", b"new")]), str(self.box.dest))
        self.assertEqual((self.box.dest / "TEA-1.png").read_bytes(), b"new")

    def test_nested_folders_are_created(self):
        zb = make_zip([("a/b/c/deep.jpg", b"d")])
        self.assertEqual(self.s.catalog.import_images(zb, str(self.box.dest)), ["a/b/c/deep.jpg"])
        self.assertTrue(os.path.isfile(self.box.dest / "a" / "b" / "c" / "deep.jpg"))

    def test_not_a_zip_is_valueerror(self):
        with self.assertRaises(ValueError):
            self.s.catalog.import_images(b"definitely not a zip", str(self.box.dest))
        self.assertEqual(self.box.files(), [])
        self.assertEqual(self.s.events.of_type("images_imported"), [])
