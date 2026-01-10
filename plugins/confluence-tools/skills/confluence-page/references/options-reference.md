# Confluence Page - Options Reference

## Arguments

### Positional Arguments

| Argument | Description |
|----------|-------------|
| `page_id` | Confluence page ID (numeric). Optional if using --space and --title. |

### Optional Arguments

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--space` | `-s` | string | - | Space key (required with --title) |
| `--title` | `-t` | string | - | Page title to search for |
| `--preset` | `-p` | choice | standard | Output preset: minimal, standard, full |
| `--body-length` | - | int | preset | Max body characters (0=none, -1=full) |
| `--include-labels` | - | flag | false | Include page labels |
| `--include-ancestors` | - | flag | false | Include parent page chain |
| `--format` | `-f` | choice | compact | Output format: compact, text, json |
| `--no-cache` | - | flag | false | Bypass cache, fetch fresh |

## Preset Details

### minimal
- Body: None (0 chars)
- Labels: No
- Ancestors: No
- Use case: Quick page existence check, get URL

### standard
- Body: 500 characters (truncated)
- Labels: No
- Ancestors: No
- Use case: General page lookup, quick summary

### full
- Body: Complete content
- Labels: Yes
- Ancestors: Yes
- Use case: Read full documentation, understand page context

## Output Format Details

### compact
Single-line primary info with minimal formatting:
```
PAGE|{id}|{title}|{space}|{status}
Body: {truncated_body}
Labels: {comma_separated}
Path: {ancestor1} > {ancestor2} > {ancestor3}
URL:{url}
```

### text
Human-readable multi-line format:
```
Page: {title}
ID: {id}
Space: {space_key}
Status: {status}
Version: {version}
Path: {ancestor_chain}
Labels: {labels}
Body: {body}
URL: {url}
```

### json
Machine-readable JSON:
```json
{
  "id": "123456",
  "title": "Page Title",
  "space": "SPACEKEY",
  "status": "current",
  "version": 5,
  "url": "https://...",
  "body": "Content...",
  "labels": ["label1", "label2"],
  "ancestors": [{"id": "1", "title": "Parent"}]
}
```

## Error Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | Page not found or API error |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CONFLUENCE_BASE_URL` | Yes | Confluence instance URL (e.g., https://yoursite.atlassian.net) |
| `CONFLUENCE_EMAIL` | Yes | Atlassian account email |
| `CONFLUENCE_API_TOKEN` | Yes | API token from Atlassian account settings |
