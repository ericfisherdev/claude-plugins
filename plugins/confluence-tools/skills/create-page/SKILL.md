---
name: create-page
description: This skill MUST be used when the user asks to "create a Confluence page", "add a wiki page", "make a new page", "create documentation", "add a page to Confluence", or otherwise requests creating new Confluence pages. ALWAYS use this skill for Confluence page creation.
---

# Create Confluence Page

**IMPORTANT:** Always use this skill's Python script for creating Confluence pages. This skill uses caching for space lookups and provides token-efficient output.

## Markdown Content Handling

**CRITICAL:** When uploading markdown content to Confluence, you MUST use the `--markdown` flag:

- **Files with `.md` extension** → ALWAYS add `--markdown`
- **Content containing markdown syntax** (headers with #, lists with -, code blocks with ```) → ALWAYS add `--markdown`
- **User asks to upload/publish a markdown file** → ALWAYS add `--markdown`

Without the `--markdown` flag, markdown content will appear as raw unformatted text in Confluence.

```bash
# CORRECT - markdown file with --markdown flag
python scripts/create_confluence_page.py --space DEV --title "Docs" \
  --body-file README.md --markdown

# WRONG - markdown will show as raw text
python scripts/create_confluence_page.py --space DEV --title "Docs" \
  --body-file README.md
```

## Quick Start

Use the Python script at `scripts/create_confluence_page.py`:

```bash
# Create page in a space
python scripts/create_confluence_page.py --space DEV --title "New Feature Spec"

# Create with content
python scripts/create_confluence_page.py --space DEV --title "API Docs" \
  --body "<p>API documentation content here</p>"

# Create from markdown file (automatically converted)
python scripts/create_confluence_page.py --space DEV --title "README" \
  --body-file /path/to/README.md --markdown

# Create under a parent page
python scripts/create_confluence_page.py --space DEV --title "Child Page" \
  --parent 123456

# Create from a file
python scripts/create_confluence_page.py --space DEV --title "README" \
  --body-file /path/to/content.html
```

## Options

| Option | Description |
|--------|-------------|
| `--space`, `-s` | Space key (required) |
| `--title`, `-t` | Page title (required) |
| `--body`, `-b` | Page body in storage format (HTML) or markdown |
| `--body-file` | Read body content from file |
| `--markdown`, `-m` | Convert body content from markdown to Confluence format |
| `--parent`, `-p` | Parent page ID (creates under this page) |
| `--parent-title` | Parent page title (alternative to ID) |
| `--labels`, `-l` | Comma-separated labels to add |
| `--format`, `-f` | Output: compact (default), text, json |

## Content Format

Confluence uses "storage format" (XHTML-based). Common elements:

```html
<!-- Paragraph -->
<p>Regular text paragraph</p>

<!-- Headings -->
<h1>Heading 1</h1>
<h2>Heading 2</h2>

<!-- Lists -->
<ul>
  <li>Unordered item</li>
</ul>
<ol>
  <li>Ordered item</li>
</ol>

<!-- Code block -->
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:plain-text-body><![CDATA[print("Hello")]]></ac:plain-text-body>
</ac:structured-macro>

<!-- Info panel -->
<ac:structured-macro ac:name="info">
  <ac:rich-text-body><p>Info message</p></ac:rich-text-body>
</ac:structured-macro>

<!-- Link to another page -->
<ac:link><ri:page ri:content-title="Page Title"/></ac:link>
```

## Common Workflows

### Create Simple Documentation Page
```bash
python scripts/create_confluence_page.py \
  --space DEV \
  --title "Setup Guide" \
  --body "<h1>Setup Guide</h1><p>Follow these steps...</p>"
```

### Create Page Under Existing Parent
```bash
# Find parent page ID first, then create under it
python scripts/create_confluence_page.py \
  --space DEV \
  --title "API Reference" \
  --parent-title "Developer Documentation"
```

### Create Page with Labels
```bash
python scripts/create_confluence_page.py \
  --space DEV \
  --title "Architecture Decision Record" \
  --labels "adr,architecture,decision" \
  --body "<p>Decision: Use microservices</p>"
```

### Create from Markdown
```bash
# Native markdown support (recommended)
python scripts/create_confluence_page.py \
  --space DEV --title "README" --body-file README.md --markdown

# Alternative: via pandoc for advanced markdown features
pandoc -f markdown -t html README.md | \
  python scripts/create_confluence_page.py \
    --space DEV --title "README" --body-file -
```

## Output Formats

**compact** (default):
```
CREATED|123456|New Feature Spec|DEV
URL:https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456
```

**text**:
```
Page Created: New Feature Spec
ID: 123456
Space: DEV
URL: https://yoursite.atlassian.net/wiki/spaces/DEV/pages/123456
```

**json**:
```json
{"id":"123456","title":"New Feature Spec","space":"DEV","url":"..."}
```

## Environment Setup

Requires environment variables:
- `CONFLUENCE_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `CONFLUENCE_EMAIL` - Your Atlassian account email
- `CONFLUENCE_API_TOKEN` - API token from Atlassian account settings

## Reference

For detailed options, see `references/options-reference.md`.
