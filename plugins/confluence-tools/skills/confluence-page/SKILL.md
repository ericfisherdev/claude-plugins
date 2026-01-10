---
name: confluence-page
description: This skill MUST be used when the user asks to "get a Confluence page", "fetch page content", "show me the wiki page", "read Confluence page", "view page", or mentions a Confluence page ID or wants to retrieve page information. ALWAYS use this skill for Confluence page retrieval.
---

# Confluence Page Retrieval

**IMPORTANT:** Always use this skill's Python script for fetching Confluence pages. This skill uses caching to reduce API calls and provides token-efficient output with configurable truncation.

## Quick Start

Use the Python script at `scripts/fetch_confluence_page.py`:

```bash
# Fetch page by ID
python scripts/fetch_confluence_page.py 123456

# Fetch page by title in a space
python scripts/fetch_confluence_page.py --space DEV --title "Architecture Overview"

# Minimal output (~30 tokens)
python scripts/fetch_confluence_page.py 123456 --preset minimal

# Full content with ancestors
python scripts/fetch_confluence_page.py 123456 --preset full
```

## Presets

| Preset | Description | Approx Tokens |
|--------|-------------|---------------|
| `minimal` | Title, ID, URL only | ~30 |
| `standard` | Title, space, status, truncated body (500 chars) | ~150 |
| `full` | Full content with ancestors and labels | Variable |

## Options

| Option | Description |
|--------|-------------|
| `--space`, `-s` | Space key (required with --title) |
| `--title`, `-t` | Page title to search for |
| `--preset`, `-p` | Output preset: minimal, standard, full |
| `--body-length` | Max body characters (0=none, -1=full) |
| `--include-labels` | Include page labels |
| `--include-ancestors` | Include parent page chain |
| `--format`, `-f` | Output: compact (default), text, json |
| `--no-cache` | Bypass cache, fetch fresh |

## Output Formats

**compact** (default):
```
PAGE|123456|Architecture Overview|DEV|current
Body: This document describes the system architecture...
URL:https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456
```

**text**:
```
Page: Architecture Overview
ID: 123456
Space: DEV
Status: current
Version: 5
Body: This document describes the system architecture...
URL: https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456
```

**json**:
```json
{"id":"123456","title":"Architecture Overview","space":"DEV","status":"current","body":"...","url":"..."}
```

## Common Workflows

### Quick Page Lookup
```bash
# Get just the URL and title
python scripts/fetch_confluence_page.py 123456 --preset minimal
```

### Read Full Documentation
```bash
# Get full page content with context
python scripts/fetch_confluence_page.py 123456 --preset full
```

### Find Page by Name
```bash
# Search for a page in a specific space
python scripts/fetch_confluence_page.py --space DEV --title "API Documentation"
```

## Cache

Pages are cached for 1 hour at `~/.confluence-tools-cache.json`.

Manage cache:
```bash
python shared/confluence_cache.py info    # View cache status
python shared/confluence_cache.py clear   # Clear cache
```

## Environment Setup

Requires environment variables:
- `CONFLUENCE_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `CONFLUENCE_EMAIL` - Your Atlassian account email
- `CONFLUENCE_API_TOKEN` - API token from Atlassian account settings

## Reference

For detailed options, see `references/options-reference.md`.
