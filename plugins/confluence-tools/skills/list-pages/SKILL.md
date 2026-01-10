---
name: list-pages
description: This skill MUST be used when the user asks to "list Confluence pages", "show pages in space", "get page tree", "list wiki pages", "show children pages", "what pages are in", "list folder contents", or wants to see multiple pages/folders in a space or under a parent. Use this for bulk content listing.
---

# List Confluence Pages and Folders

**IMPORTANT:** Always use this skill's Python script for listing Confluence content. This skill supports both pages and folders, uses caching, and provides token-efficient output for content hierarchies.

## Quick Start

Use the Python script at `scripts/list_confluence_pages.py`:

```bash
# List root content in a space
python scripts/list_confluence_pages.py --space DEV

# List children of a specific page or folder
python scripts/list_confluence_pages.py --parent 123456

# List with depth (recursive)
python scripts/list_confluence_pages.py --space DEV --depth 2

# Tree view with type indicators
python scripts/list_confluence_pages.py --space DEV --depth 3 --format tree
```

## Options

| Option | Description |
|--------|-------------|
| `--space`, `-s` | Space key to list content from |
| `--parent`, `-p` | Parent page or folder ID to list children of |
| `--depth`, `-d` | Recursion depth (default: 1, max: 5) |
| `--limit`, `-l` | Maximum items to return (default: 50) |
| `--preset` | Output preset: minimal, standard, full |
| `--format`, `-f` | Output: compact (default), tree, json |
| `--no-cache` | Bypass cache, fetch fresh |

## Presets

| Preset | Description |
|--------|-------------|
| `minimal` | ID, title, and type |
| `standard` | ID, title, type, status, created date |
| `full` | All fields including child count |

## Output Formats

**compact** (default):
```
ITEMS|DEV|5
FOLDER|123456|Architecture Overview|current
PAGE|123457|API Documentation|current
PAGE|123458|Setup Guide|current
PAGE|123459|FAQ|current
PAGE|123460|Release Notes|current
```

**tree** (hierarchical with type indicators):
```
Space: DEV (5 items)
├── [F] Architecture (123456)
│   ├── [P] System Design (123461)
│   └── [P] Data Flow (123462)
├── [F] API Documentation (123457)
├── [P] Setup Guide (123458)
├── [P] FAQ (123459)
└── [P] Release Notes (123460)
```

Type indicators:
- `[F]` = Folder
- `[P]` = Page

**json**:
```json
{"space":"DEV","count":5,"pages":[{"id":"123456","title":"Architecture","type":"folder","children":[...]},...]}
```

## Common Workflows

### List Space Contents
```bash
# Quick overview of a space
python scripts/list_confluence_pages.py --space DEV --preset minimal

# Full tree structure with types
python scripts/list_confluence_pages.py --space DEV --depth 3 --format tree
```

### List Children of a Folder
```bash
# Direct children only (auto-detects if parent is folder or page)
python scripts/list_confluence_pages.py --parent 123456

# All descendants
python scripts/list_confluence_pages.py --parent 123456 --depth 5
```

### List Children of a Page
```bash
# Works the same way - auto-detects parent type
python scripts/list_confluence_pages.py --parent 789012
```

### Find Content for Navigation
```bash
# Get content tree for building navigation
python scripts/list_confluence_pages.py --space DEV --depth 2 --format json
```

## Folder Support

This skill automatically handles both pages and folders:

1. **Auto-detection** - When using `--parent`, the script automatically detects whether the ID is a page or folder
2. **Mixed content** - Results include both folders and pages with type indicators
3. **Recursive** - Folder contents are fetched recursively up to the specified depth

## Cache

Content listings are cached for 4 hours at `~/.confluence-tools-cache.json`.

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
