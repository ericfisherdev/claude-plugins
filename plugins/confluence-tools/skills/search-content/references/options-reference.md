# Search Content - Options Reference

## Arguments

At least one search criterion is required.

| Argument | Type | Description |
|----------|------|-------------|
| `query` | string | Search text (positional, optional) |

## Optional Arguments

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--space` | `-s` | string | - | Limit search to specific space |
| `--type` | `-t` | choice | - | Content type: page, blogpost, comment |
| `--label` | `-l` | string | - | Search for content with specific label |
| `--contributor` | - | string | - | Search by content contributor |
| `--modified-after` | - | date | - | Content modified after date (YYYY-MM-DD) |
| `--modified-before` | - | date | - | Content modified before date (YYYY-MM-DD) |
| `--limit` | - | int | 25 | Maximum results |
| `--format` | `-f` | choice | compact | Output format: compact, text, json |

## CQL Query Building

The script builds Confluence Query Language (CQL) queries from the provided options:

| Option | CQL Translation |
|--------|-----------------|
| `query "text"` | `text ~ "text"` |
| `--space DEV` | `space = "DEV"` |
| `--type page` | `type = page` |
| `--label "api"` | `label = "api"` |
| `--contributor "user"` | `contributor = "user"` |
| `--modified-after 2024-01-01` | `lastModified >= "2024-01-01"` |
| `--modified-before 2024-12-31` | `lastModified <= "2024-12-31"` |

Multiple options are combined with AND.

## Content Types

| Type | Description |
|------|-------------|
| `page` | Standard Confluence pages |
| `blogpost` | Blog posts |
| `comment` | Comments on pages/posts |

## Output Format Details

### compact
```
SEARCH|{count}|"{query}"
HIT|{id}|{title}|{space}|{type}
HIT|{id}|{title}|{space}|{type}
...
```

### text
```
Search Results: "{query}" ({count} found)

1. {title}
   ID: {id} | Space: {space} | Type: {type}
   URL: {url}

2. {title}
   ID: {id} | Space: {space} | Type: {type}
   URL: {url}
...
```

### json
```json
{
  "query": "search text",
  "count": 5,
  "results": [
    {
      "id": "123456",
      "title": "Page Title",
      "space": "SPACEKEY",
      "type": "page",
      "url": "https://..."
    }
  ]
}
```

## Search Examples

### Basic Text Search
```bash
python search_confluence.py "authentication"
```

### Space-Scoped Search
```bash
python search_confluence.py "API" --space DEV
```

### Label Search
```bash
python search_confluence.py --label "architecture"
```

### Combined Filters
```bash
python search_confluence.py "security" \
  --space DEV \
  --type page \
  --label "reviewed" \
  --modified-after 2024-01-01
```

### Find All Pages in Space
```bash
python search_confluence.py --space DEV --type page --limit 100
```

### Recent Changes
```bash
python search_confluence.py --space DEV --modified-after 2024-01-01
```

### Contributor Search
```bash
python search_confluence.py --contributor "john.smith" --type page
```

## Search Tips

1. **Exact Phrases**: Use quotes for exact matching
   ```bash
   python search_confluence.py '"authentication flow"'
   ```

2. **Wildcards**: CQL supports wildcards
   - `auth*` matches "authentication", "authorization", etc.

3. **Boolean Logic**: Multiple criteria use AND
   - To find pages with EITHER label, run separate searches

4. **Date Ranges**: Combine `--modified-after` and `--modified-before`
   ```bash
   python search_confluence.py --space DEV \
     --modified-after 2024-01-01 \
     --modified-before 2024-06-30
   ```

## Error Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success (even if no results) |
| 1 | Error - API error, authentication failed |

## Limitations

- Maximum 25 results by default (configurable with `--limit`)
- CQL has a complexity limit on Confluence Cloud
- Some advanced CQL features may not be available on all versions

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CONFLUENCE_BASE_URL` | Yes | Confluence instance URL |
| `CONFLUENCE_EMAIL` | Yes | Atlassian account email |
| `CONFLUENCE_API_TOKEN` | Yes | API token from Atlassian account settings |
