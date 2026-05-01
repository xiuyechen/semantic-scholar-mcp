# Semantic Scholar MCP Server

An [MCP](https://modelcontextprotocol.io) server that gives Claude access to [Semantic Scholar](https://www.semanticscholar.org/)'s database of 200M+ academic papers. Search papers, explore citation graphs, and look up authors — directly from Claude. Wraps the official [`semanticscholar`](https://pypi.org/project/semanticscholar/) SDK with a process-wide rate limiter to prevent 429s under concurrent dispatch.

## Tools

| Tool | Description |
|------|-------------|
| `search_papers` | Keyword search with filters for year range, fields of study, and open-access availability |
| `get_paper` | Get full details for a paper by Semantic Scholar ID, DOI, ArXiv ID, or PubMed ID |
| `get_citations` | Navigate the citation graph — find papers that cite a given paper, or papers it references |
| `get_author` | Look up an author's profile, h-index, and publication metrics |
| `search_by_author` | Find an author by name and list their top papers |

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A Semantic Scholar API key (see below — strongly recommended)

### Get an API key

Without a key, requests share a global anonymous rate-limit bucket and you will see frequent `429 Too Many Requests` errors during normal use. Request a free key at [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api#api-key) — turnaround is usually a few days.

Once you have a key, set it as an environment variable:

```bash
export S2_API_KEY=your_key_here
```

For persistence across shells, add the line to `~/.zshenv` (or your shell's equivalent).

### Install

```bash
git clone https://github.com/xiuyechen/semantic-scholar-mcp.git
cd semantic-scholar-mcp
uv pip install -e .
```

Or with pip:

```bash
pip install -e .
```

### Rate limiting and retries

The client wraps the official [`semanticscholar`](https://pypi.org/project/semanticscholar/) Python SDK and adds a process-wide async token bucket on top. Concurrent calls from the same process serialize through a 1.05s floor so the client cannot burst past the API's 1 req/sec limit, even when an LLM dispatches multiple tools in parallel. Transient 429s are retried with `Retry-After`-aware exponential backoff (up to 5 attempts). No tuning required.

## Configure with Claude

### Claude Code

```bash
claude mcp add semantic-scholar -- semantic-scholar-mcp
```

Or with an API key:

```bash
claude mcp add semantic-scholar -e S2_API_KEY=your_key -- semantic-scholar-mcp
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "semantic-scholar": {
      "command": "semantic-scholar-mcp",
      "env": {
        "S2_API_KEY": "your_key_here"
      }
    }
  }
}
```

## Example Usage

Once configured, you can ask Claude things like:

- "Search for recent papers on protein structure prediction"
- "Find the paper with DOI 10.1038/s41586-021-03819-2 and summarize it"
- "What papers cite AlphaFold2? Show me the most influential ones"
- "Look up David Baker's publication record"
- "Find open-access papers on CRISPR gene editing from 2024"

## API Reference

This server wraps the [Semantic Scholar Academic Graph API](https://api.semanticscholar.org/api-docs/). The API is free to use and covers:

- 200M+ papers from all major publishers
- 2.4B+ citation edges
- Author profiles with h-index and affiliation data
- Open access PDF links where available
- AI-generated TLDR summaries for many papers

## License

MIT
