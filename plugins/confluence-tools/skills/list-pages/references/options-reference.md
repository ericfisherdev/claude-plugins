# List Pages - Options Reference

## Arguments

At least one of `--space` or `--parent` is required.

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--space` | `-s` | string | Space key to list pages from |
| `--parent` | `-p` | string | Parent page ID to list children of |

## Optional Arguments

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--depth` | `-d` | int | 1 | Recursion depth (1-5) |
| `--limit` | `-l` | int | 50 | Maximum pages per level |
| `--preset` | - | choice | standard | Output preset: minimal, standard, full |
| `--format` | `-f` | choice | compact | Output format: compact, tree, json |
| `--no-cache` | - | flag | false | Bypass cache, fetch fresh |

## Presets

### minimal
Fields: `id`, `title`

### standard
Fields: `id`, `title`, `status`, `createdAt`

### full
Fields: `id`, `title`, `status`, `createdAt`, `childCount`

## Output Format Details

### compact
Flat list with pipe-separated fields:
```
PAGES|{space_key}|{total_count}
PAGE|{id}|{title}|{status}|{createdAt}
PAGE|{id}|{title}|{status}|{createdAt}
  PAGE|{id}|{title}|{status}|{createdAt}  # Indented children
```

### tree
Visual tree structure:
```
Space: SPACEKEY (N pages)
├── Page Title (id)
│   ├── Child Page (id)
│   └── Another Child (id)
├── Second Page (id)
└── Third Page (id)
```

### json
Full JSON structure with nested children:
```json
{
  "space": "SPACEKEY",
  "count": 10,
  "pages": [
    {
      "id": "123456",
      "title": "Page Title",
      "status": "current",
      "createdAt": "2024-01-15T10:30:00Z",
      "children": [
        {
          "id": "123457",
          "title": "Child Page",
          ...
        }
      ]
    }
  ]
}
```

## Depth Behavior

| Depth | Description |
|-------|-------------|
| 1 | Direct children only (default) |
| 2 | Children and grandchildren |
| 3 | Three levels deep |
| 4 | Four levels deep |
| 5 | Maximum depth (five levels) |

**Note:** Higher depth values increase API calls and response size.

## Usage Patterns

### List Root Pages in Space
```bash
python list_confluence_pages.py --space DEV
```

### List All Documentation Structure
```bash
python list_confluence_pages.py --space DEV --depth 5 --format tree
```

### List Children of Specific Page
```bash
python list_confluence_pages.py --parent 123456 --depth 2
```

### Quick ID Lookup
```bash
python list_confluence_pages.py --space DEV --preset minimal
```

### Export Page Structure
```bash
python list_confluence_pages.py --space DEV --depth 3 --format json > structure.json
```

## Error Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success (even if no pages found) |
| 1 | Error - space not found, API error |

## Cache

Page listings are cached with 4-hour TTL. Use `--no-cache` to force fresh data.

Cache location: `~/.confluence-tools-cache.json`

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CONFLUENCE_BASE_URL` | Yes | Confluence instance URL |
| `CONFLUENCE_EMAIL` | Yes | Atlassian account email |
| `CONFLUENCE_API_TOKEN` | Yes | API token from Atlassian account settings |
