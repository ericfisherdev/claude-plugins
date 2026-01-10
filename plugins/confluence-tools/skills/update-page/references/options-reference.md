# Update Page - Options Reference

## Required Arguments

| Argument | Description |
|----------|-------------|
| `page_id` | Confluence page ID to update |

## Optional Arguments

At least one update option is required.

### Content Updates

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--title` | `-t` | string | New page title |
| `--body` | `-b` | string | New page body (replaces existing content) |
| `--body-file` | - | path | Read body from file (use '-' for stdin) |
| `--append` | `-a` | string | Append content to existing body |
| `--prepend` | - | string | Prepend content to existing body |

### Label Management

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--labels` | `-l` | string | Set labels (comma-separated, replaces existing) |
| `--add-labels` | - | string | Add labels to existing (comma-separated) |
| `--remove-labels` | - | string | Remove specific labels (comma-separated) |

### Version Control

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--minor-edit` | - | flag | Mark as minor edit (no notifications) |
| `--version-message` | - | string | Version comment/message |

### Output

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--format` | `-f` | choice | compact | Output format: compact, text, json |

## Body Update Modes

### Replace (`--body` or `--body-file`)
Completely replaces the page content:
```bash
python update_confluence_page.py 123456 --body "<p>All new content</p>"
```

### Append (`--append`)
Adds content at the end of existing body:
```bash
python update_confluence_page.py 123456 --append "<h2>New Section</h2><p>Details...</p>"
```

### Prepend (`--prepend`)
Adds content at the beginning of existing body:
```bash
python update_confluence_page.py 123456 --prepend "<ac:structured-macro ac:name='warning'><ac:rich-text-body><p>Deprecated</p></ac:rich-text-body></ac:structured-macro>"
```

## Label Operations

### Replace All Labels
```bash
python update_confluence_page.py 123456 --labels "final,reviewed,v2"
# Removes all existing labels, adds these three
```

### Add Labels
```bash
python update_confluence_page.py 123456 --add-labels "reviewed,approved"
# Keeps existing labels, adds new ones (duplicates ignored)
```

### Remove Labels
```bash
python update_confluence_page.py 123456 --remove-labels "draft,wip"
# Removes specified labels, keeps others
```

### Combine Add and Remove
```bash
python update_confluence_page.py 123456 --add-labels "final" --remove-labels "draft"
```

## Version Management

The script automatically:
1. Fetches the current page version
2. Increments the version number
3. Submits the update with the new version

### Minor Edit
```bash
python update_confluence_page.py 123456 --body "..." --minor-edit
# Watchers won't be notified
```

### Version Message
```bash
python update_confluence_page.py 123456 --body "..." \
  --version-message "Updated API documentation for v2.0 release"
```

## Output Format Details

### compact
```
UPDATED|{page_id}|{title}|v{version}
Changes:{comma_separated_changes}
URL:{confluence_url}
```

### text
```
Page Updated: {title}
ID: {page_id}
Version: {version}
Changes: {comma_separated_changes}
URL: {confluence_url}
```

### json
```json
{
  "id": "page_id",
  "title": "Page Title",
  "version": 6,
  "changes": ["title", "body", "labels"],
  "url": "https://..."
}
```

## Change Types

The `changes` field indicates what was modified:

| Change | Description |
|--------|-------------|
| `title` | Page title was changed |
| `body` | Page body was replaced |
| `append` | Content was appended |
| `prepend` | Content was prepended |
| `labels` | Labels were added or removed |

## Error Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success - page updated |
| 1 | Error - page not found, version conflict, or API error |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CONFLUENCE_BASE_URL` | Yes | Confluence instance URL |
| `CONFLUENCE_EMAIL` | Yes | Atlassian account email |
| `CONFLUENCE_API_TOKEN` | Yes | API token from Atlassian account settings |
