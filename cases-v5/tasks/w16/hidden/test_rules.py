import html.parser
import unittest

from hidden.helpers import login, make_shop

ACTIVE_TAGS = {"script", "style", "iframe", "frame", "frameset", "object", "embed", "applet",
               "img", "svg", "math", "link", "meta", "base", "form", "input", "button",
               "textarea", "select", "video", "audio", "source", "template", "image"}
URL_ATTRS = {"href", "src", "action", "formaction", "xlink:href", "data", "poster", "background"}
BAD_SCHEMES = ("javascript:", "vbscript:", "data:")


class _Tags(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []

    def handle_starttag(self, tag, attrs):
        self.found.append((tag.lower(), [(k.lower(), v or "") for k, v in attrs]))

    handle_startendtag = handle_starttag


def problems(markup):
    p = _Tags()
    p.feed(markup)
    p.close()
    out = []
    for tag, attrs in p.found:
        if tag in ACTIVE_TAGS:
            out.append("<%s> element" % tag)
        for k, v in attrs:
            if k.startswith("on") or k in ("style", "srcdoc"):
                out.append("%s attribute on <%s>" % (k, tag))
            if k in URL_ATTRS:
                squeezed = "".join(ch for ch in v if ch.isprintable() and not ch.isspace()).lower()
                if squeezed.startswith(BAD_SCHEMES):
                    out.append("%s=%r on <%s>" % (k, v, tag))
    return out


class DescriptionsCannotCarryScript(unittest.TestCase):
    def check(self, sources):
        s, _, _ = make_shop()
        root = login(s, "root")
        bad = []
        for src in sources:
            code, body = s.api.set_description(root, {"sku": "TEA-1", "text": src})
            if 400 <= code < 500:
                continue                          # refusing the description is acceptable
            self.assertEqual(code, 200)
            for rendered in (body["html"], s.catalog.description_html("TEA-1")):
                if problems(rendered):
                    bad.append((src, rendered, problems(rendered)))
        self.assertEqual(bad, [])

    def test_raw_html_is_not_rendered_as_markup(self):
        """V1.3.5: HTML typed into a description does not reach the page as live elements."""
        self.check([
            "Lovely tea <script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "Try **this** <iframe src=https://evil.example></iframe>",
            '<div onmouseover="alert(1)">hover me</div>',
            "<svg onload=alert(1)>",
            '<a href="javascript:alert(1)">click</a>',
            "[<img src=x onerror=alert(1)>](https://shop.example/tea)",
        ])

    def test_links_cannot_run_script(self):
        """V1.3.5: a markup link cannot target a script-running URL scheme."""
        self.check([
            "[click](javascript:alert(1))",
            "[click](JaVaScRiPt:alert%281%29)",
            "[click](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)",
            "[click](vbscript:msgbox)",
            "[click](java&#115;cript:alert(1))",
        ])

    def test_link_url_cannot_add_attributes(self):
        """V1.3.5: a markup link URL cannot break out of the href and add attributes."""
        self.check([
            '[x](https://shop.example/"onmouseover="alert(1))',
            "[x](https://shop.example/'onfocus='alert(1))",
            '[x](https://shop.example/"style="background:url(x))',
        ])
