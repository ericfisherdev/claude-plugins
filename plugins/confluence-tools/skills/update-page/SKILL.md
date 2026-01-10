---
name: update-page
description: This skill MUST be used when the user asks to "update a Confluence page", "edit wiki page", "modify page content", "change page title", "append to page", "update documentation", or otherwise requests modifying existing Confluence pages. ALWAYS use this skill for Confluence page updates.
---

# Update Confluence Page

**IMPORTANT:** Always use this skill's Python script for updating Confluence pages. This skill handles version management automatically and provides token-efficient output.

## Markdown Content Handling

**CRITICAL:** When uploading markdown content to Confluence, you MUST use the `--markdown` flag:

- **Files with `.md` extension** → ALWAYS add `--markdown`
- **Content containing markdown syntax** (headers with #, lists with -, code blocks with ```) → ALWAYS add `--markdown`
- **User asks to upload/update with a markdown file** → ALWAYS add `--markdown`

Without the `--markdown` flag, markdown content will appear as raw unformatted text in Confluence.

```bash
# CORRECT - markdown file with --markdown flag
python scripts/update_confluence_page.py 123456 --body-file README.md --markdown

# WRONG - markdown will show as raw text
python scripts/update_confluence_page.py 123456 --body-file README.md
```

## Quick Start

Use the Python script at `scripts/update_confluence_page.py`:

```bash
# Update page title
python scripts/update_confluence_page.py 123456 --title "New Title"

# Update page body
python scripts/update_confluence_page.py 123456 --body "<p>New content</p>"

# Update from markdown file (automatically converted)
python scripts/update_confluence_page.py 123456 --body-file /path/to/README.md --markdown

# Append content to existing page
python scripts/update_confluence_page.py 123456 --append "<p>Additional content</p>"

# Update from file
python scripts/update_confluence_page.py 123456 --body-file /path/to/content.html

# Add/remove labels
python scripts/update_confluence_page.py 123456 --add-labels "reviewed,approved"
python scripts/update_confluence_page.py 123456 --remove-labels "draft"
```

## Options

| Option | Description |
|--------|-------------|
| `--title`, `-t` | New page title |
| `--body`, `-b` | New page body (replaces existing) |
| `--body-file` | Read body from file (use '-' for stdin) |
| `--markdown`, `-m` | Convert body/append/prepend from markdown to Confluence format |
| `--append`, `-a` | Append content to existing body |
| `--prepend` | Prepend content to existing body |
| `--labels`, `-l` | Set labels (replaces existing) |
| `--add-labels` | Add labels to existing |
| `--remove-labels` | Remove specific labels |
| `--minor-edit` | Mark as minor edit (no notifications) |
| `--version-message` | Version comment/message |
| `--format`, `-f` | Output: compact (default), text, json |

## Version Management

Confluence requires a version number for updates. This script:
1. Fetches current page version automatically
2. Increments version number
3. Submits update with new version

No manual version tracking needed.

## Common Workflows

### Update Documentation Content
```bash
python scripts/update_confluence_page.py 123456 \
  --body "<h1>Updated Guide</h1><p>New instructions...</p>" \
  --version-message "Updated instructions for v2.0"
```

### Append Meeting Notes
```bash
python scripts/update_confluence_page.py 123456 \
  --append "<h2>Meeting 2024-01-15</h2><p>Notes from today...</p>" \
  --minor-edit
```

### Update Title Only
```bash
python scripts/update_confluence_page.py 123456 \
  --title "Architecture Overview (Updated)"
```

### Manage Labels
```bash
# Add labels
python scripts/update_confluence_page.py 123456 --add-labels "reviewed,qa-passed"

# Remove labels
python scripts/update_confluence_page.py 123456 --remove-labels "draft,wip"

# Replace all labels
python scripts/update_confluence_page.py 123456 --labels "final,published"
```

### Update from Markdown
```bash
# Native markdown support (recommended)
python scripts/update_confluence_page.py 123456 --body-file updated-docs.md --markdown

# Alternative: via pandoc for advanced markdown features
pandoc -f markdown -t html updated-docs.md | \
  python scripts/update_confluence_page.py 123456 --body-file -
```

## Output Formats

**compact** (default):
```
UPDATED|123456|Page Title|v6
Changes:title,body,labels
URL:https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456
```

**text**:
```
Page Updated: Page Title
ID: 123456
Version: 6
Changes: title, body, labels
URL: https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456
```

**json**:
```json
{"id":"123456","title":"Page Title","version":6,"changes":["title","body","labels"],"url":"..."}
```

## Environment Setup

Requires environment variables:
- `CONFLUENCE_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `CONFLUENCE_EMAIL` - Your Atlassian account email
- `CONFLUENCE_API_TOKEN` - API token from Atlassian account settings

## Reference

For detailed options, see `references/options-reference.md`.
