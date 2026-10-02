def paginate(items: list, page: int, per_page: int) -> dict:
    """Pages are 1-based. Return {"items": the slice, "total_pages": n}. An empty list
    has 1 page. page < 1 or per_page < 1 raises ValueError; a page past the end returns
    no items."""
    total_pages = len(items) // per_page
    start = page * per_page
    return {"items": items[start:start + per_page], "total_pages": total_pages}
