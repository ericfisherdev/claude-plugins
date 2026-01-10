---
name: list-pages
description: This skill MUST be used when the user asks to "list Confluence pages", "show pages in space", "get page tree", "list wiki pages", "show children pages", "what pages are in", or wants to see multiple pages in a space or under a parent. Use this for bulk page listing.
---

# List Confluence Pages

**IMPORTANT:** Always use this skill's Python script for listing Confluence pages. This skill uses caching and provides token-efficient output for page hierarchies.

## Quick Start

Use the Python script at `scripts/list_confluence_pages.py`:

```bash
# List root pages in a space
python scripts/list_confluence_pages.py --space DEV

# List children of a specific page
python scripts/list_confluence_pages.py --parent 123456

# List with depth (recursive)
python scripts/list_confluence_pages.py --space DEV --depth 2

# Minimal output for quick overview
python scripts/list_confluence_pages.py --space DEV --preset minimal
```

## Options

| Option | Description |
|--------|-------------|
| `--space`, `-s` | Space key to list pages from |
| `--parent`, `-p` | Parent page ID to list children of |
| `--depth`, `-d` | Recursion depth (default: 1, max: 5) |
| `--limit`, `-l` | Maximum pages to return (default: 50) |
| `--preset` | Output preset: minimal, standard, full |
| `--format`, `-f` | Output: compact (default), tree, json |
| `--no-cache` | Bypass cache, fetch fresh |

## Presets

| Preset | Description |
|--------|-------------|
| `minimal` | ID and title only |
| `standard` | ID, title, status, created date |
| `full` | All fields including child count |

## Output Formats

**compact** (default):
```
PAGES|DEV|5
PAGE|123456|Architecture Overview|current
PAGE|123457|API Documentation|current
PAGE|123458|Setup Guide|current
PAGE|123459|FAQ|current
PAGE|123460|Release Notes|current
```

**tree** (hierarchical):
```
Space: DEV (5 pages)
├── Architecture Overview (123456)
│   ├── System Design (123461)
│   └── Data Flow (123462)
├── API Documentation (123457)
├── Setup Guide (123458)
├── FAQ (123459)
└── Release Notes (123460)
```

**json**:
```json
{"space":"DEV","count":5,"pages":[{"id":"123456","title":"Architecture Overview","children":[...]},...]}
```

## Common Workflows

### List Space Contents
```bash
# Quick overview of a space
python scripts/list_confluence_pages.py --space DEV --preset minimal

# Full tree structure
python scripts/list_confluence_pages.py --space DEV --depth 3 --format tree
```

### List Children of a Page
```bash
# Direct children only
python scripts/list_confluence_pages.py --parent 123456

# All descendants
python scripts/list_confluence_pages.py --parent 123456 --depth 5
```

### Find Pages for Navigation
```bash
# Get page tree for building navigation
python scripts/list_confluence_pages.py --space DEV --depth 2 --format json
```

## Cache

Page listings are cached for 4 hours at `~/.confluence-tools-cache.json`.

```bash
# Force fresh data
python scripts/list_confluence_pages.py --space DEV --no-cache
```

## Environment Setup

Requires environment variables:
- `CONFLUENCE_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `CONFLUENCE_EMAIL` - Your Atlassian account email
- `CONFLUENCE_API_TOKEN` - API token from Atlassian account settings

## Reference

For detailed options, see `references/options-reference.md`.
