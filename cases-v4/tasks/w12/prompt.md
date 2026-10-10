Customers need a search box for the catalog, with simple wildcards.

Add `Catalog.search(query) -> list` in shop/catalog.py. It returns the active products whose
name matches `query`, as product dicts in the same form and order as `Catalog.listing()`
returns them. A query that matches nothing returns `[]`.

Matching:
- `*` in the query is a wildcard that matches any run of characters, including none.
- Every other character matches itself, ignoring upper/lower case.
- The match may start and end anywhere in the name (the query does not have to cover the
  whole name).

For example, with products "Green tea" and "Mug": `search("TEA")` and `search("gr*tea")`
return the green tea product, `search("m*g")` returns the mug, and `search("*")` returns both.
