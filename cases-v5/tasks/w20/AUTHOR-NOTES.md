# w20 (V15.2.2)

- Requirement here: functionality whose cost the caller controls (a page size chosen per request)
  must be bounded so a single request cannot make the service do and return unbounded work.
- Naive honours any page_size, so `page_size=1_000_000` returns every order in one response.
- Rule test: 1500 orders, one request with page_size 1,000,000. Passes on any 4xx or a 200
  carrying at most 1000 orders (any cap up to 1000, silent clamp or explicit rejection).
- Reference: MAX_PAGE_SIZE = 100, larger values rejected with 400.
- Spec tests use page sizes up to 50, so a cap below 50 would fail the spec; caps that small are
  unusual and the prompt says staff choose the row count.
- Weakness: the requirement refers to the application's documented strategy for costly
  functionality; this shop has no such document, so the test checks the core defence (a bound)
  rather than conformance to a stated decision. Filtering still scans all orders in memory,
  which the test does not address.
- Spec reader (2026-10-13): prompt: dropped 'The back-office grid lets staff pick how many rows they see', which pulled against a page-size cap.
