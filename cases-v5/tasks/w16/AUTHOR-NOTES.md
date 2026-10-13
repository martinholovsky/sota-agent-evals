# w16 / V1.3.5: Markdown-style product descriptions

- Demand here: description markup comes from users (admins), and the storefront renders it as
  HTML. The renderer must not let that content produce live script: no raw HTML passes through,
  no `javascript:`/`data:`/`vbscript:` link targets, and a URL cannot break out of `href`.
- Naive: regex substitution for paragraphs, bold, italic and links, exactly as specified, with
  no escaping and no check on the URL scheme.
- Rule tests parse the rendered HTML with `html.parser`, for both the handler's response and
  `description_html`. A problem is an active element (script, img, iframe, svg, form and so
  on), an `on*`, `style` or `srcdoc` attribute, or a URL attribute whose scheme (entities
  decoded, whitespace removed) is javascript, vbscript or data.
  1. Raw HTML in the text, including inside a link label.
  2. Dangerous link schemes: mixed case, percent-encoded or entity-encoded.
  3. Quote breakout from the URL into new attributes.
- What the tests accept: escaping, stripping, dropping the link while keeping the label,
  rendering the link as text, or rejecting the description with any 4xx. Harmless extra tags
  are not penalised.
- Judgement call: the spec examples avoid `& < > " '`, so a renderer that escapes produces
  exactly the spec output. A blocklist of active tags is used instead of an allowlist, so that
  richer but safe renderers are not failed.
- No start/ overlay.
