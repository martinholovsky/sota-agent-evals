def paginate(items: list, page: int, per_page: int) -> dict:
    if page < 1 or per_page < 1:
        raise ValueError("page and per_page must be >= 1")
    total_pages = max(1, -(-len(items) // per_page))
    start = (page - 1) * per_page
    return {"items": items[start:start + per_page], "total_pages": total_pages}
