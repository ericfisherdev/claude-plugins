---
name: create-folder
description: This skill MUST be used when the user asks to "create a Confluence folder", "make a folder in wiki", "organize pages", or wants to create organizational structure in Confluence. Creates true Confluence folders only (no fallback to pages).
---

# Create Confluence Folder

**IMPORTANT:** This skill creates true Confluence folders using the Confluence Cloud folders API. It does NOT fall back to creating pages as containers - if folder creation fails, it will provide clear error messages and suggestions.

## Quick Start

Use the Python script at `scripts/create_confluence_folder.py`:

```bash
# Create folder in a space
python scripts/create_confluence_folder.py --space DEV --title "Documentation"

# Create nested folder under existing folder
python scripts/create_confluence_folder.py --space DEV --title "API Docs" --parent 123456
```

## Options

| Option | Description |
|--------|-------------|
| `--space`, `-s` | Space key (required) |
| `--title`, `-t` | Folder title (required) |
| `--parent`, `-p` | Parent folder ID (creates nested folder) |
| `--parent-title` | Parent folder title (alternative to ID) |
| `--format`, `-f` | Output: compact (default), text, json |

## Important Notes

1. **True folders only** - This skill only creates true Confluence folders. It will NOT silently create pages as a fallback.

2. **Folder API availability** - The Confluence folders API is available in Confluence Cloud. If folder creation fails, the script will provide helpful error messages.

3. **Nesting folders** - When creating nested folders, the parent must be an existing folder (not a page).

## Common Workflows

### Create Documentation Structure
```bash
# Create root folders in a space
python scripts/create_confluence_folder.py --space DEV --title "Architecture"
python scripts/create_confluence_folder.py --space DEV --title "API Documentation"
python scripts/create_confluence_folder.py --space DEV --title "Guides"
```

### Create Nested Structure
```bash
# Create a parent folder first
python scripts/create_confluence_folder.py --space DEV --title "Documentation"

# Then create child folders under it (use the ID from the previous command)
python scripts/create_confluence_folder.py --space DEV --title "v1" --parent 123456
python scripts/create_confluence_folder.py --space DEV --title "v2" --parent 123456
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
Type: folder
URL: https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456
```

**json**:
```json
{"id":"123456","title":"Documentation","space":"DEV","type":"folder","url":"..."}
```

## Error Handling

If folder creation fails, the script will:
1. Display a clear error message
2. Suggest alternatives (create manually in Confluence UI, check permissions, etc.)
3. Exit with a non-zero status code

Common errors:
- **Folder API not available** - Try creating the folder in the Confluence web UI
- **Folder already exists** - A folder with that title already exists in this location
- **Permission denied** - Check your Confluence permissions

## Environment Setup

Requires environment variables:
- `CONFLUENCE_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `CONFLUENCE_EMAIL` - Your Atlassian account email
- `CONFLUENCE_API_TOKEN` - API token from Atlassian account settings

## Reference

For detailed options, see `references/options-reference.md`.
