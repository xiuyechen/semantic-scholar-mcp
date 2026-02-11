# Semantic Scholar MCP Server

An [MCP](https://modelcontextprotocol.io) server that gives Claude access to [Semantic Scholar](https://www.semanticscholar.org/)'s database of 225M+ academic papers. Search papers, explore citation graphs, and look up authors — directly from Claude.

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

### (Optional) API key

The server works without an API key, but rate limits are shared across all unauthenticated users. For better rate limits, get a free key from [Semantic Scholar API](https://www.semanticscholar.org/product/api) and set it:

```bash
export S2_API_KEY=your_key_here
```

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

- 225M+ papers from all major publishers
- 2.8B+ citation edges
- Author profiles with h-index and affiliation data
- Open access PDF links where available
- AI-generated TLDR summaries for many papers

## License

MIT
