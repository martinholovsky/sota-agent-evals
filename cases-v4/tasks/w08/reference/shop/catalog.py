"""Products. A SKU is uppercase letters/digits/hyphens, 3-20 chars."""
import io
import pathlib
import re
import stat
import zipfile

SKU_RE = re.compile(r"[A-Z0-9-]{3,20}")


class Catalog:
    def __init__(self, events):
        self.events = events
        self._products = {}          # sku -> {"sku", "name", "price", "active"}

    def add(self, sku: str, name: str, price: int) -> dict:
        if not SKU_RE.fullmatch(sku):
            raise ValueError("bad sku: %r" % sku)
        if sku in self._products:
            raise ValueError("duplicate sku: %s" % sku)
        if not isinstance(price, int) or isinstance(price, bool) or price <= 0:
            raise ValueError("price must be positive int cents")
        p = {"sku": sku, "name": name, "price": price, "active": True}
        self._products[sku] = p
        self.events.emit("product_added", sku=sku, price=price)
        return dict(p)

    def get(self, sku: str) -> dict:
        if sku not in self._products:
            raise KeyError(sku)
        return dict(self._products[sku])

    def set_price(self, sku: str, price: int) -> None:
        if sku not in self._products:
            raise KeyError(sku)
        if not isinstance(price, int) or isinstance(price, bool) or price <= 0:
            raise ValueError("price must be positive int cents")
        old = self._products[sku]["price"]
        self._products[sku]["price"] = price
        self.events.emit("price_changed", sku=sku, old=old, new=price)

    def listing(self) -> list:
        """Active products, sorted by SKU."""
        return [dict(p) for _, p in sorted(self._products.items()) if p["active"]]

    MAX_ENTRIES = 10_000
    MAX_TOTAL_BYTES = 500 * 1024 * 1024
    MAX_RATIO = 100

    def import_images(self, zip_bytes: bytes, dest_dir: str) -> list:
        """Zip Slip and zip-bomb safe (sota-code-security rules/01 §4, rules/09)."""
        try:
            z = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except zipfile.BadZipFile as e:
            raise ValueError("not a zip archive") from e
        base = pathlib.Path(dest_dir).resolve()
        with z:
            infos = [i for i in z.infolist() if not i.is_dir()]
            if len(z.infolist()) > self.MAX_ENTRIES:
                raise ValueError("too many entries")
            plan = []
            for info in infos:                       # validate every entry before writing any
                name = info.filename
                if "\0" in name or name.startswith(("/", "\\")) or pathlib.PurePosixPath(name).is_absolute() \
                        or (len(name) > 1 and name[1] == ":"):
                    raise ValueError("absolute entry: %r" % name)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError("symlink entry: %r" % name)
                target = (base / name).resolve()
                if not target.is_relative_to(base) or target == base:
                    raise ValueError("entry escapes destination: %r" % name)
                plan.append((info, target))
            total = 0
            for info, target in plan:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.parent.resolve().is_relative_to(base):
                    raise ValueError("entry escapes destination: %r" % info.filename)
                written = 0
                with z.open(info) as src, open(target, "wb") as out:
                    while chunk := src.read(64 * 1024):
                        written += len(chunk)
                        total += len(chunk)
                        if total > self.MAX_TOTAL_BYTES:
                            raise ValueError("archive too large when decompressed")
                        if info.compress_size and written / info.compress_size > self.MAX_RATIO \
                                and written > 1024 * 1024:
                            raise ValueError("compression ratio too high")
                        out.write(chunk)
        names = sorted(info.filename for info, _ in plan)
        self.events.emit("images_imported", count=len(names))
        return names
