"""Async client for the Semantic Scholar Academic Graph API.

Wraps the official `semanticscholar` PyPI SDK and adds a process-wide rate
limiter on top. The SDK handles request shaping, auth headers, and per-call
retry; the rate limiter enforces a hard floor between request *starts* so
the client cannot burst even when callers issue concurrent requests.
"""

import asyncio
import os
import time
from dataclasses import dataclass

from semanticscholar import AsyncSemanticScholar

# SS rate limits: 1 req/sec for both anonymous (shared) and authenticated (dedicated).
# Set the floor slightly above 1.0s to absorb clock skew and avoid edge-case 429s.
MIN_REQUEST_INTERVAL = 1.05  # seconds


class _RateLimiter:
    """Process-wide async token bucket — one request per MIN_REQUEST_INTERVAL."""

    def __init__(self, interval: float):
        self.interval = interval
        self._lock = asyncio.Lock()
        self._next_allowed = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._next_allowed - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
            self._next_allowed = now + self.interval


_LIMITER = _RateLimiter(MIN_REQUEST_INTERVAL)


# Field lists kept here (not passed through to the SDK's defaults) so that
# server.py output formatting can rely on stable response shapes.
PAPER_SEARCH_FIELDS = [
    "title", "abstract", "year", "authors", "citationCount",
    "influentialCitationCount", "openAccessPdf", "fieldsOfStudy",
    "tldr", "externalIds", "url", "venue", "publicationDate",
]

PAPER_DETAIL_FIELDS = PAPER_SEARCH_FIELDS + ["referenceCount", "citationStyles"]

AUTHOR_FIELDS = [
    "name", "affiliations", "paperCount", "citationCount", "hIndex", "url",
]

AUTHOR_PAPER_FIELDS = [
    "title", "year", "citationCount", "venue", "openAccessPdf", "externalIds", "url",
]

CITATION_FIELDS = [
    "title", "year", "authors", "citationCount", "venue", "externalIds", "url",
]


def _raw(obj) -> dict:
    """Extract the underlying API dict from an SDK model object."""
    return getattr(obj, "raw_data", None) or {}


def _paginated_to_dict(result, total: int | None = None) -> dict:
    """Adapt a PaginatedResults to the {"data": [...], "total": N} shape
    server.py expects."""
    items = [_raw(p) for p in result.items]
    return {"data": items, "total": total if total is not None else getattr(result, "total", len(items))}


@dataclass
class S2Client:
    """Async client wrapping the semanticscholar SDK with rate limiting."""

    api_key: str | None = None
    timeout: int = 30

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("S2_API_KEY")
        # `retry=True` makes the SDK retry on transient errors itself; combined
        # with our token bucket, this gives belt-and-suspenders coverage.
        self._sdk = AsyncSemanticScholar(
            api_key=self.api_key,
            timeout=self.timeout,
            retry=True,
        )

    async def search_papers(
        self,
        query: str,
        year_range: str | None = None,
        fields_of_study: list[str] | None = None,
        open_access_only: bool = False,
        limit: int = 10,
        offset: int = 0,  # accepted for back-compat; SDK paginates internally
    ) -> dict:
        """Search for papers by keyword query."""
        await _LIMITER.acquire()
        kwargs: dict = {
            "query": query,
            "fields": PAPER_SEARCH_FIELDS,
            "limit": min(limit, 100),
        }
        if year_range:
            kwargs["year"] = year_range
        if fields_of_study:
            kwargs["fields_of_study"] = fields_of_study
        if open_access_only:
            kwargs["open_access_pdf"] = True
        result = await self._sdk.search_paper(**kwargs)
        return _paginated_to_dict(result)

    async def get_paper(self, paper_id: str) -> dict:
        await _LIMITER.acquire()
        paper = await self._sdk.get_paper(paper_id, fields=PAPER_DETAIL_FIELDS)
        return _raw(paper)

    async def get_citations(
        self,
        paper_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        await _LIMITER.acquire()
        result = await self._sdk.get_paper_citations(
            paper_id, fields=CITATION_FIELDS, limit=min(limit, 100),
        )
        # Citations API wraps each item as {"citingPaper": {...}}; SDK exposes
        # this via .raw_data which preserves the wrapper.
        return _paginated_to_dict(result)

    async def get_references(
        self,
        paper_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        await _LIMITER.acquire()
        result = await self._sdk.get_paper_references(
            paper_id, fields=CITATION_FIELDS, limit=min(limit, 100),
        )
        return _paginated_to_dict(result)

    async def get_author(self, author_id: str) -> dict:
        await _LIMITER.acquire()
        author = await self._sdk.get_author(author_id, fields=AUTHOR_FIELDS)
        return _raw(author)

    async def search_authors(self, query: str, limit: int = 5) -> dict:
        await _LIMITER.acquire()
        result = await self._sdk.search_author(
            query, fields=AUTHOR_FIELDS, limit=min(limit, 20),
        )
        return _paginated_to_dict(result)

    async def get_author_papers(
        self,
        author_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        await _LIMITER.acquire()
        result = await self._sdk.get_author_papers(
            author_id, fields=AUTHOR_PAPER_FIELDS, limit=min(limit, 100),
        )
        return _paginated_to_dict(result)
