import html
import re

_RX = re.compile(r"\{\{\{\s*(\w+)\s*\}\}\}|\{\{\s*(\w+)\s*\}\}")


def render(template: str, context: dict) -> str:
    def sub(m):
        raw, esc = m.group(1), m.group(2)
        name = raw or esc
        if name not in context:
            raise KeyError(name)
        v = str(context[name])
        return v if raw else html.escape(v, quote=True)
    return _RX.sub(sub, template)
