"""MCP server exposing Semantic Scholar tools to Claude."""

import json

from mcp.server.fastmcp import FastMCP

from .client import S2Client

mcp = FastMCP("semantic-scholar")
client = S2Client()


# --- Formatting helpers ---

def _fmt_authors(authors: list[dict], max_show: int = 5) -> str:
    names = [a.get("name", "Unknown") for a in authors[:max_show]]
    result = ", ".join(names)
    if len(authors) > max_show:
        result += f" (+{len(authors) - max_show} more)"
    return result


def _fmt_paper(p: dict, index: int | None = None) -> str:
    prefix = f"{index}. " if index is not None else ""
    title = p.get("title", "Untitled")
    year = p.get("year", "n/a")
    authors = _fmt_authors(p.get("authors", []))
    venue = p.get("venue", "")
    citations = p.get("citationCount", 0)
    doi = None
    ext = p.get("externalIds") or {}
    if ext.get("DOI"):
        doi = ext["DOI"]

    lines = [f"{prefix}**{title}**"]
    lines.append(f"  {authors} ({year})")
    if venue:
        lines.append(f"  {venue}")
    lines.append(f"  Citations: {citations}")

    tldr = p.get("tldr")
    if tldr and isinstance(tldr, dict):
        lines.append(f"  TLDR: {tldr.get('text', '')}")

    if doi:
        lines.append(f"  DOI: {doi}")

    oa = p.get("openAccessPdf")
    if oa and isinstance(oa, dict) and oa.get("url"):
        lines.append(f"  Open Access PDF: {oa['url']}")

    s2_url = p.get("url")
    if s2_url:
        lines.append(f"  Semantic Scholar: {s2_url}")

    return "\n".join(lines)


def _fmt_paper_list(papers: list[dict], total: int | None = None) -> str:
    if not papers:
        return "No papers found."
    parts = []
    if total is not None:
        parts.append(f"Found {total} results (showing {len(papers)}):\n")
    for i, p in enumerate(papers, 1):
        parts.append(_fmt_paper(p, index=i))
    return "\n\n".join(parts)


def _fmt_author(a: dict) -> str:
    name = a.get("name", "Unknown")
    affiliations = a.get("affiliations", [])
    h_index = a.get("hIndex", "n/a")
    paper_count = a.get("paperCount", "n/a")
    citation_count = a.get("citationCount", "n/a")
    url = a.get("url", "")

    lines = [f"**{name}**"]
    if affiliations:
        lines.append(f"  Affiliations: {', '.join(affiliations)}")
    lines.append(f"  h-index: {h_index} | Papers: {paper_count} | Citations: {citation_count}")
    if url:
        lines.append(f"  {url}")
    return "\n".join(lines)


# --- Tools ---

@mcp.tool()
async def search_papers(
    query: str,
    year_range: str | None = None,
    fields_of_study: list[str] | None = None,
    open_access_only: bool = False,
    limit: int = 10,
) -> str:
    """Search Semantic Scholar for academic papers.

    Args:
        query: Search query (e.g., "protein structure prediction",
               "machine learning drug discovery")
        year_range: Optional year filter. Examples: "2020-2026", "2024-", "-2020"
        fields_of_study: Optional field filter. Examples: ["Biology"],
                         ["Computer Science", "Medicine"]. Valid fields include:
                         Biology, Medicine, Chemistry, Computer Science,
                         Physics, Mathematics, Engineering, and more.
        open_access_only: If true, only return papers with free PDF access
        limit: Max results (default 10, max 100)
    """
    try:
        result = await client.search_papers(
            query, year_range, fields_of_study, open_access_only, limit,
        )
    except Exception as e:
        return f"Error searching papers: {e}"

    papers = [item for item in result.get("data", [])]
    total = result.get("total", len(papers))
    return _fmt_paper_list(papers, total)


@mcp.tool()
async def get_paper(paper_id: str) -> str:
    """Get detailed information about a specific paper.

    Args:
        paper_id: Paper identifier. Accepts multiple formats:
                  - Semantic Scholar ID: "649def34f8be52c8b66281af98ae884c09aef38b"
                  - DOI: "DOI:10.1038/nature12373"
                  - ArXiv ID: "ARXIV:2106.15928"
                  - PubMed ID: "PMID:19872477"
                  - Corpus ID: "CorpusId:215416146"
    """
    try:
        paper = await client.get_paper(paper_id)
    except Exception as e:
        return f"Error fetching paper: {e}"

    lines = [_fmt_paper(paper)]

    abstract = paper.get("abstract")
    if abstract:
        lines.append(f"\n**Abstract:**\n{abstract}")

    fos = paper.get("fieldsOfStudy")
    if fos:
        lines.append(f"\nFields of study: {', '.join(fos)}")

    ref_count = paper.get("referenceCount", 0)
    cite_count = paper.get("citationCount", 0)
    inf_count = paper.get("influentialCitationCount", 0)
    lines.append(f"\nReferences: {ref_count} | Citations: {cite_count} | Influential citations: {inf_count}")

    return "\n".join(lines)


@mcp.tool()
async def get_citations(
    paper_id: str,
    direction: str = "citing",
    limit: int = 20,
) -> str:
    """Navigate the citation graph for a paper.

    Args:
        paper_id: Paper identifier (S2 ID, DOI:..., ARXIV:..., etc.)
        direction: "citing" = papers that cite this one,
                   "cited-by" = papers this one references
        limit: Max results (default 20, max 100)
    """
    try:
        if direction == "cited-by":
            result = await client.get_references(paper_id, limit)
            label = "references (papers this one cites)"
        else:
            result = await client.get_citations(paper_id, limit)
            label = "citations (papers that cite this one)"
    except Exception as e:
        return f"Error fetching citations: {e}"

    items = result.get("data", [])
    # Citations/references are wrapped: {"citingPaper": {...}} or {"citedPaper": {...}}
    papers = []
    for item in items:
        p = item.get("citingPaper") or item.get("citedPaper") or item
        if p.get("title"):
            papers.append(p)

    if not papers:
        return f"No {label} found."

    header = f"Showing {len(papers)} {label}:\n"
    parts = [header]
    for i, p in enumerate(papers, 1):
        parts.append(_fmt_paper(p, index=i))
    return "\n\n".join(parts)


@mcp.tool()
async def get_author(author_id: str) -> str:
    """Get an author's profile and publication metrics.

    Args:
        author_id: Semantic Scholar author ID (numeric string, e.g., "1741101")
    """
    try:
        author = await client.get_author(author_id)
    except Exception as e:
        return f"Error fetching author: {e}"

    return _fmt_author(author)


@mcp.tool()
async def search_by_author(
    author_name: str,
    limit: int = 10,
) -> str:
    """Search for an author and list their recent papers.

    Finds the best-matching author by name, then returns their profile
    and most-cited papers.

    Args:
        author_name: Author name to search (e.g., "Yoshiki Sasai")
        limit: Max papers to return (default 10)
    """
    try:
        author_results = await client.search_authors(author_name, limit=3)
    except Exception as e:
        return f"Error searching authors: {e}"

    authors = author_results.get("data", [])
    if not authors:
        return f"No authors found matching '{author_name}'."

    # Use the top match
    top = authors[0]
    author_id = top.get("authorId")
    profile = _fmt_author(top)

    if not author_id:
        return profile

    try:
        papers_result = await client.get_author_papers(author_id, limit=limit)
    except Exception as e:
        return f"{profile}\n\nError fetching papers: {e}"

    papers = [item.get("paper", item) for item in papers_result.get("data", [])]
    # Sort by citation count descending
    papers.sort(key=lambda p: p.get("citationCount", 0) or 0, reverse=True)

    lines = [profile, f"\nTop papers ({len(papers)} shown):\n"]
    for i, p in enumerate(papers, 1):
        title = p.get("title", "Untitled")
        year = p.get("year", "")
        cites = p.get("citationCount", 0)
        venue = p.get("venue", "")
        year_str = f" ({year})" if year else ""
        venue_str = f" — {venue}" if venue else ""
        lines.append(f"  {i}. {title}{year_str}{venue_str} [{cites} citations]")

    return "\n".join(lines)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
