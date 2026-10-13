# w09 - V1.2.10

- Demand here: a CSV export opened in a spreadsheet must not let a cell whose text begins with a
  formula-trigger character (= + - @ tab NUL) run as a formula; such a cell gets a leading single
  quote. RFC 4180 quoting of commas/quotes/line breaks is the other half.
- Naive: `csv.writer` over the raw names. It already does RFC 4180 quoting (so that half is a
  spec test, `test_punctuation_round_trips`, not a rule test), but writes `=HYPERLINK(...)` as is.
- Rule tests accept any cell that begins with `'` and still contains the original name somewhere
  after it (so extra escaping inside is tolerated); they reject a cell that keeps the trigger
  character first, or that drops/mangles the text. Both `products_csv` and the API body are checked.
- Judgement call: rejecting such names at `Catalog.add` is NOT accepted - the requirement is about
  the export, and names like "-20% bundle" are legitimate catalogue text. A solution that strips
  the trigger character instead of quoting also fails (it loses data and is not the mechanism
  the requirement names).
- The reference also applies the helper to `orders_csv` text cells; not tested.
- Spec reader (2026-10-13): prompt: 'must come back intact' replaced by 'must stay in one name cell, commas and quotes included', so a leading-quote escape no longer looks like it contradicts the ticket.
