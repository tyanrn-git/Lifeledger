from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass(frozen=True)
class PageResult:
    items: list
    page: int
    per_page: int
    total: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 1
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def parse_page(raw: str | None, *, default: int = 1) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


def page_offset(page: int, per_page: int) -> int:
    return (page - 1) * per_page


def build_query(base: dict[str, str | None], *, page: int | None = None) -> str:
    params = {k: v for k, v in base.items() if v not in (None, "")}
    if page is not None:
        params["page"] = str(page)
    return urlencode(params)
