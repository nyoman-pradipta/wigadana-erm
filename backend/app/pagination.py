"""Helper pagination generik — dipakai di semua router yang punya listing panjang."""
from fastapi import Query
from sqlalchemy.orm import Query as SAQuery

PER_PAGE_DEFAULT = 10


def page_params(
    page: int = Query(1, ge=1, description="Halaman, mulai dari 1"),
    per_page: int = Query(PER_PAGE_DEFAULT, ge=1, le=100, description="Item per halaman"),
) -> tuple[int, int]:
    return page, per_page


def paginate(query: SAQuery, page: int, per_page: int) -> tuple[list, int, int]:
    """Return (items, total, total_pages) — 1 count query + 1 slice query."""
    total = query.order_by(None).count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total, total_pages
