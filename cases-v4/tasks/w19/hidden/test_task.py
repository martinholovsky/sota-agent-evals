import struct
import unittest
import zlib

from hidden.helpers import make_shop


def _chunk(kind, body):
    return (struct.pack(">I", len(body)) + kind + body
            + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))


# A real 1x1 RGB PNG: signature, IHDR, IDAT (filter byte + one pixel), IEND, correct CRCs.
PNG = (b"\x89PNG\r\n\x1a\n"
       + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
       + _chunk(b"IDAT", zlib.compress(b"\x00\x2e\x8b\x57"))
       + _chunk(b"IEND", b""))

# A real 1x1 baseline (SOF0) JPEG, 632 bytes, written by Pillow 12.3.0 (quality 75) and checked
# to decode with Pillow and macOS sips on 2026-10-10.
JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912"
    "130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffdb0043010909"
    "090c0b0c180d0d1832211c21323232323232323232323232323232323232323232323232323232323232323232323232"
    "3232323232323232323232323232ffc00011080001000103012200021101031101ffc4001f0000010501010101010100"
    "000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d010203000411051221"
    "31410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a"
    "434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a9293949596979899"
    "9aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1"
    "f2f3f4f5f6f7f8f9faffc4001f0100030101010101010101010000000000000102030405060708090a0bffc400b51100"
    "020102040403040705040400010277000102031104052131061241510761711322328108144291a1b1c109233352f015"
    "6272d10a162434e125f11718191a262728292a35363738393a434445464748494a535455565758595a63646566676869"
    "6a737475767778797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4"
    "c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9faffda000c03010002110311003f00c8"
    "a28a2b98f9a3ffd9")


class Store:
    def __init__(self):
        self.files = {}
        self.puts = []

    def put(self, name, data):
        self.puts.append(name)
        self.files[name] = data


def setup():
    s, gw, clock = make_shop()
    s.catalog.image_store = Store()
    return s, s.catalog.image_store


def try_upload(s, sku, filename, data):
    try:
        return s.catalog.upload_image(sku, filename, data)
    except Exception as e:                                  # a refusal of any kind
        return e


class Spec(unittest.TestCase):
    def test_png_is_stored_and_linked(self):
        s, store = setup()
        p = s.catalog.upload_image("TEA-1", "tea.png", PNG)
        name = s.catalog.get("TEA-1")["image"]
        self.assertEqual(p["image"], name)
        self.assertEqual(p["sku"], "TEA-1")
        self.assertEqual(store.files[name], PNG)
        evs = s.events.of_type("product_image_set")
        self.assertEqual([(e["sku"], e["image"]) for e in evs], [("TEA-1", name)])

    def test_jpeg_is_stored(self):
        s, store = setup()
        s.catalog.upload_image("MUG-1", "mug.jpg", JPEG)
        self.assertEqual(store.files[s.catalog.get("MUG-1")["image"]], JPEG)

    def test_other_file_type_is_refused(self):
        s, store = setup()
        with self.assertRaises(ValueError):
            s.catalog.upload_image("TEA-1", "notes.txt", b"just some text\n")
        self.assertEqual(store.puts, [])
        self.assertNotIn("image", s.catalog.get("TEA-1"))
        self.assertEqual(s.events.of_type("product_image_set"), [])

    def test_unknown_sku(self):
        s, store = setup()
        with self.assertRaises(KeyError):
            s.catalog.upload_image("NOPE-1", "x.png", PNG)
        self.assertEqual(store.puts, [])

    def test_reupload_replaces(self):
        s, store = setup()
        s.catalog.upload_image("TEA-1", "a.png", PNG)
        s.catalog.upload_image("TEA-1", "b.jpg", JPEG)
        self.assertEqual(store.files[s.catalog.get("TEA-1")["image"]], JPEG)
        self.assertEqual(len(s.events.of_type("product_image_set")), 2)

    def test_no_image_key_by_default(self):
        s, store = setup()
        self.assertNotIn("image", s.catalog.get("TEA-1"))
