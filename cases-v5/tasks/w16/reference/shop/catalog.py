"""Products. A SKU is uppercase letters/digits/hyphens, 3-20 chars."""
import html
import re

SKU_RE = re.compile(r"[A-Z0-9-]{3,20}")

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
EM_RE = re.compile(r"\*(.+?)\*")
PARA_SPLIT_RE = re.compile(r"\n[ \t]*\n")
SAFE_SCHEMES = ("http", "https", "mailto")


def _safe_url(escaped_url: str) -> bool:
    """Allow http(s)/mailto and scheme-less (relative) URLs; anything else is refused."""
    raw = html.unescape(escaped_url)
    cleaned = "".join(ch for ch in raw if ch.isprintable() and not ch.isspace())
    scheme, colon, _ = cleaned.partition(":")
    if not colon or "/" in scheme or "?" in scheme or "#" in scheme:
        return True                                  # relative URL
    return scheme.lower() in SAFE_SCHEMES


def _link(m) -> str:
    label, url = m.group(1), m.group(2)
    if not _safe_url(url):
        return label                                 # keep the text, drop the link
    return '<a href="%s">%s</a>' % (url, label)


def _inline(text: str) -> str:
    # Escape first: admins type text, never raw HTML; only our markup produces tags.
    text = html.escape(text, quote=True)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = EM_RE.sub(r"<em>\1</em>", text)
    return LINK_RE.sub(_link, text)


def render_markup(text: str) -> str:
    """Description markup -> HTML: paragraphs, line breaks, **bold**, *italic*, [label](url).

    Any HTML in the source is shown as text, and links only use http(s), mailto or relative
    URLs, so a description cannot put script into the storefront page.
    """
    paras = [p.strip() for p in PARA_SPLIT_RE.split(text.replace("\r\n", "\n"))]
    return "\n".join("<p>%s</p>" % _inline(p).replace("\n", "<br>") for p in paras if p)


class Catalog:
    def __init__(self, events):
        self.events = events
        self._products = {}          # sku -> {"sku", "name", "price", "active"}
        self._descriptions = {}      # sku -> markup source text

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

    def set_description(self, sku: str, text: str) -> None:
        if sku not in self._products:
            raise KeyError(sku)
        self._descriptions[sku] = text
        self.events.emit("description_changed", sku=sku)

    def description_html(self, sku: str) -> str:
        if sku not in self._products:
            raise KeyError(sku)
        return render_markup(self._descriptions.get(sku, ""))
