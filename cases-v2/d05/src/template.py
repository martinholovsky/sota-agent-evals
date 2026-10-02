def render(template: str, context: dict) -> str:
    """Replace placeholders with values from context.
    - {{ name }} inserts str(value) HTML-ESCAPED (& < > " ' all escaped).
    - {{{ name }}} inserts str(value) RAW, unescaped.
    - Whitespace inside the braces is optional: {{name}} == {{  name  }}.
    - A name missing from context raises KeyError naming it.
    - Text outside placeholders is unchanged; there is no nesting."""
    raise NotImplementedError
