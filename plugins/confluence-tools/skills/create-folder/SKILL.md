---
name: create-folder
description: This skill MUST be used when the user asks to "create a Confluence folder", "make a folder in wiki", "create a page container", "organize pages", "create parent page for documents", or wants to create organizational structure in Confluence. Use this for creating folder-like pages.
---

# Create Confluence Folder

**IMPORTANT:** In Confluence, "folders" are typically created as pages that serve as organizational containers for child pages. This skill creates either a true Confluence folder (where supported) or a minimal page that acts as a folder.

## Quick Start

Use the Python script at `scripts/create_confluence_folder.py`:

```bash
# Create folder in a space
python scripts/create_confluence_folder.py --space DEV --title "Documentation"

# Create nested folder under existing page
python scripts/create_confluence_folder.py --space DEV --title "API Docs" --parent 123456

# Create with description
python scripts/create_confluence_folder.py --space DEV --title "Archives" \
  --description "Historical documentation"
```

## Options

| Option | Description |
|--------|-------------|
| `--space`, `-s` | Space key (required) |
| `--title`, `-t` | Folder title (required) |
| `--parent`, `-p` | Parent page ID (creates nested folder) |
| `--parent-title` | Parent page title (alternative to ID) |
| `--description`, `-d` | Brief description (shown on folder page) |
| `--format`, `-f` | Output: compact (default), text, json |

## How It Works

Confluence has two approaches for folder-like organization:

### 1. Folder Content Type (Confluence Cloud)
Where supported, creates an actual folder object that can contain pages without being a page itself.

### 2. Container Page (Fallback)
Creates a minimal page with:
- Title only (or optional description)
- Serves as parent for child pages
- Standard folder icon appearance

This skill automatically uses the best available method.

## Common Workflows

### Create Documentation Structure
```bash
# Create root folders
python scripts/create_confluence_folder.py --space DEV --title "Architecture"
python scripts/create_confluence_folder.py --space DEV --title "API Documentation"
python scripts/create_confluence_folder.py --space DEV --title "Guides"

# Create nested structure
python scripts/create_confluence_folder.py --space DEV --title "v1" --parent-title "API Documentation"
python scripts/create_confluence_folder.py --space DEV --title "v2" --parent-title "API Documentation"
```

### Organize Existing Content
```bash
# Create a folder, then move pages into it
python scripts/create_confluence_folder.py --space DEV --title "Legacy Docs" \
  --description "Documentation for deprecated features"
```

### Create Archive Folder
```bash
python scripts/create_confluence_folder.py --space DEV --title "Archive" \
  --description "Historical documents - read only"
```

## Output Formats

**compact** (default):
```
FOLDER|123456|Documentation|DEV
URL:https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456
```

**text**:
```
Folder Created: Documentation
ID: 123456
Space: DEV
Type: page (container)
URL: https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456
```

**json**:
```json
{"id":"123456","title":"Documentation","space":"DEV","type":"page","url":"..."}
```

## Folder vs Page

| Feature | Folder | Page |
|---------|--------|------|
| Contains children | Yes | Yes |
| Has body content | Optional | Yes |
| Appears in tree | Yes | Yes |
| Can be edited | Limited | Full |
| Icon | Folder icon | Page icon |

## Environment Setup

Requires environment variables:
- `CONFLUENCE_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `CONFLUENCE_EMAIL` - Your Atlassian account email
- `CONFLUENCE_API_TOKEN` - API token from Atlassian account settings

## Reference

For detailed options, see `references/options-reference.md`.
