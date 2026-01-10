---
name: search-content
description: This skill MUST be used when the user asks to "search Confluence", "find pages", "search wiki", "look for documentation", "find content about", or wants to search for pages across Confluence. Use this for content discovery and search.
---

# Search Confluence Content

**IMPORTANT:** Always use this skill's Python script for searching Confluence. This skill provides CQL-based search with token-efficient output, including parent hierarchy information.

## Quick Start

Use the Python script at `scripts/search_confluence.py`:

```bash
# Simple text search
python scripts/search_confluence.py "authentication"

# Search in specific space
python scripts/search_confluence.py "API documentation" --space DEV

# Search with type filter
python scripts/search_confluence.py "meeting notes" --type blogpost

# Search by label
python scripts/search_confluence.py --label "architecture"
```

## Options

| Option | Description |
|--------|-------------|
| `query` | Search text (positional argument) |
| `--space`, `-s` | Limit search to specific space |
| `--type`, `-t` | Content type: page, blogpost, comment |
| `--label`, `-l` | Search for content with specific label |
| `--contributor` | Search by content contributor |
| `--modified-after` | Content modified after date (YYYY-MM-DD) |
| `--modified-before` | Content modified before date (YYYY-MM-DD) |
| `--limit` | Maximum results (default: 25) |
| `--format`, `-f` | Output: compact (default), text, json |

## Search Types

### Text Search
Search in page titles and content:
```bash
python scripts/search_confluence.py "deployment guide"
```

### Label Search
Find pages with specific labels:
```bash
python scripts/search_confluence.py --label "api-reference"
```

### Combined Search
```bash
python scripts/search_confluence.py "authentication" --space DEV --label "security"
```

## CQL (Confluence Query Language)

This skill uses CQL internally. Advanced users can leverage CQL patterns:

| Search Pattern | CQL Equivalent |
|---------------|----------------|
| Text search | `text ~ "query"` |
| Space filter | `space = "KEY"` |
| Type filter | `type = page` |
| Label filter | `label = "name"` |
| Date filter | `lastModified >= "2024-01-01"` |

## Common Workflows

### Find Documentation
```bash
# Find all API-related docs
python scripts/search_confluence.py "API" --space DEV --type page

# Find recent changes
python scripts/search_confluence.py "" --space DEV --modified-after 2024-01-01
```

### Find Meeting Notes
```bash
python scripts/search_confluence.py "meeting notes" --type blogpost --limit 10
```

### Find by Label
```bash
# Find all architecture decisions
python scripts/search_confluence.py --label "adr"

# Find deprecated content
python scripts/search_confluence.py --label "deprecated" --space DEV
```

### Find Contributor's Content
```bash
python scripts/search_confluence.py --contributor "john.smith" --space DEV
```

## Output Formats

**compact** (default):
```
SEARCH|5|"authentication"
HIT|123456|Authentication Guide|DEV|page|parent:Security Docs
HIT|123457|OAuth Setup|DEV|page|parent:Authentication Guide
HIT|123458|SSO Integration|DEV|page|parent:Authentication Guide
HIT|123459|Security Best Practices|DEV|page
HIT|123460|Login Flow|DEV|page|parent:User Management
```

Note: Parent information is included when available (e.g., `parent:Security Docs`).

**text**:
```
Search Results: "authentication" (5 found)

1. Authentication Guide
   ID: 123456 | Space: DEV | Type: page | Parent: Security Docs
   URL: https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456

2. OAuth Setup
   ID: 123457 | Space: DEV | Type: page | Parent: Authentication Guide
   URL: https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123457
...
```

**json**:
```json
{
  "query": "authentication",
  "count": 5,
  "results": [
    {
      "id": "123456",
      "title": "Authentication Guide",
      "space": "DEV",
      "type": "page",
      "url": "...",
      "parentId": "123400",
      "parentTitle": "Security Docs"
    }
  ]
}
```

## Parent Information

Search results now include parent/hierarchy information when available:
- **parentId** - ID of the direct parent page or folder
- **parentTitle** - Title of the direct parent

This helps understand where each result is located in the content hierarchy.

## Environment Setup

Requires environment variables:
- `CONFLUENCE_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `CONFLUENCE_EMAIL` - Your Atlassian account email
- `CONFLUENCE_API_TOKEN` - API token from Atlassian account settings

## Reference

For detailed options, see `references/options-reference.md`.
