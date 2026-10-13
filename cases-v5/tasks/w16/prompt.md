# Formatted product descriptions

Admins want to write product descriptions with a little formatting, and the storefront shows
them as HTML under each product. Add a small markup language (a subset of Markdown).

## Markup

- Paragraphs are separated by one or more blank lines. Each paragraph is stripped of leading
  and trailing whitespace and wrapped in `<p>...</p>`; paragraphs are joined with `"\n"`.
  A single newline inside a paragraph becomes `<br>`.
- `**text**` renders as `<strong>text</strong>`.
- `*text*` renders as `<em>text</em>`.
- `[label](url)` renders as `<a href="url">label</a>`. The label may itself contain
  `**bold**` or `*italic*`.
- A description that is empty or only whitespace renders as `""`.

## Interface

- `Catalog.set_description(sku: str, text: str) -> None`: stores the description. `KeyError`
  for an unknown SKU. Emits one `description_changed` event with `sku`.
- `Catalog.description_html(sku: str) -> str`: the rendered HTML (`""` if no description was
  set). `KeyError` for an unknown SKU.
- `Api.set_description(principal, req)` with `req = {"sku": str, "text": str}`: requires the
  `catalog:edit` permission (403 otherwise); 400 if `sku` or `text` is not a string; 404 for an
  unknown SKU; on success `200, {"sku": sku, "html": <rendered html>}`.

Example: `"Our **best** green tea.\n\nSee [the farm](https://farm.example/tea)."` renders as
`<p>Our <strong>best</strong> green tea.</p>\n<p>See <a href="https://farm.example/tea">the farm</a>.</p>`.

Keep the README conventions.
