"""Async client for the Semantic Scholar Academic Graph API."""

import asyncio
import os
from dataclasses import dataclass

import httpx

BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Fields we request by default for paper searches
PAPER_SEARCH_FIELDS = ",".join([
    "title", "abstract", "year", "authors", "citationCount",
    "influentialCitationCount", "openAccessPdf", "fieldsOfStudy",
    "tldr", "externalIds", "url", "venue", "publicationDate",
])

PAPER_DETAIL_FIELDS = ",".join([
    "title", "abstract", "year", "authors", "citationCount",
    "influentialCitationCount", "openAccessPdf", "fieldsOfStudy",
    "tldr", "externalIds", "url", "venue", "publicationDate",
    "referenceCount", "citationStyles",
])

AUTHOR_FIELDS = ",".join([
    "name", "affiliations", "paperCount", "citationCount", "hIndex", "url",
])

AUTHOR_PAPER_FIELDS = ",".join([
    "title", "year", "citationCount", "venue", "openAccessPdf", "externalIds", "url",
])

CITATION_FIELDS = ",".join([
    "title", "year", "authors", "citationCount", "venue", "externalIds", "url",
])


@dataclass
class S2Client:
    """Thin async wrapper around the Semantic Scholar API."""

    api_key: str | None = None
    timeout: float = 30.0

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("S2_API_KEY")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                resp = await client.get(
                    f"{BASE_URL}{path}",
                    params=params,
                    headers=self._headers(),
                )
                if resp.status_code == 429 and attempt < 2:
                    await asyncio.sleep(1 + attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
        return {}  # unreachable, satisfies type checker

    async def search_papers(
        self,
        query: str,
        year_range: str | None = None,
        fields_of_study: list[str] | None = None,
        open_access_only: bool = False,
        limit: int = 10,
        offset: int = 0,
    ) -> dict:
        """Search for papers by keyword query."""
        params: dict = {
            "query": query,
            "fields": PAPER_SEARCH_FIELDS,
            "limit": min(limit, 100),
            "offset": offset,
        }
        if year_range:
            params["year"] = year_range
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)
        if open_access_only:
            params["openAccessPdf"] = ""
        return await self._get("/paper/search", params)

    async def get_paper(self, paper_id: str) -> dict:
        """Get details for a single paper.

        paper_id can be: S2 paper ID, DOI (prefix with DOI:),
        ArXiv ID (prefix with ARXIV:), or other external IDs.
        """
        params = {"fields": PAPER_DETAIL_FIELDS}
        return await self._get(f"/paper/{paper_id}", params)

    async def get_citations(
        self,
        paper_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Get papers that cite this paper."""
        params = {
            "fields": CITATION_FIELDS,
            "limit": min(limit, 100),
            "offset": offset,
        }
        return await self._get(f"/paper/{paper_id}/citations", params)

    async def get_references(
        self,
        paper_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Get papers that this paper cites."""
        params = {
            "fields": CITATION_FIELDS,
            "limit": min(limit, 100),
            "offset": offset,
        }
        return await self._get(f"/paper/{paper_id}/references", params)

    async def get_author(self, author_id: str) -> dict:
        """Get author profile by Semantic Scholar author ID."""
        params = {"fields": AUTHOR_FIELDS}
        return await self._get(f"/author/{author_id}", params)

    async def search_authors(self, query: str, limit: int = 5) -> dict:
        """Search for authors by name."""
        params = {
            "query": query,
            "fields": AUTHOR_FIELDS,
            "limit": min(limit, 20),
        }
        return await self._get("/author/search", params)

    async def get_author_papers(
        self,
        author_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Get papers by a specific author."""
        params = {
            "fields": AUTHOR_PAPER_FIELDS,
            "limit": min(limit, 100),
            "offset": offset,
        }
        return await self._get(f"/author/{author_id}/papers", params)
