# Create Folder - Options Reference

## Required Arguments

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--space` | `-s` | string | Space key where the folder will be created |
| `--title` | `-t` | string | Folder title |

## Optional Arguments

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--parent` | `-p` | string | - | Parent page ID (creates nested folder) |
| `--parent-title` | - | string | - | Parent page title (alternative to --parent) |
| `--description` | `-d` | string | - | Brief description (shown on folder page) |
| `--format` | `-f` | choice | compact | Output format: compact, text, json |

## Folder Creation Behavior

This skill attempts two creation methods:

### 1. True Folder (Primary)
Uses Confluence's folder API (available in newer Confluence Cloud instances):
- Creates a native folder object
- Folders can contain pages but are not pages themselves
- May not be available on all Confluence versions

### 2. Container Page (Fallback)
If folder API is unavailable, creates a minimal page:
- Page with title and optional description
- Serves as organizational parent for child pages
- Functions identically to a folder for navigation purposes

## Output Format Details

### compact
```
FOLDER|{id}|{title}|{space_key}
URL:{confluence_url}
```

### text
```
Folder Created: {title}
ID: {id}
Space: {space_key}
Type: {folder|page (container)}
Parent ID: {parent_id}  (if applicable)
URL: {confluence_url}
```

### json
```json
{
  "id": "page_id",
  "title": "Folder Title",
  "space": "SPACEKEY",
  "type": "folder",
  "parentId": "parent_id",
  "url": "https://..."
}
```

## Type Values

| Type | Description |
|------|-------------|
| `folder` | Native Confluence folder (v2 API) |
| `page (container)` | Page acting as folder (fallback) |

## Usage Examples

### Create Root-Level Folder
```bash
python create_confluence_folder.py --space DEV --title "Documentation"
```

### Create Nested Folder Structure
```bash
# Create parent folder
python create_confluence_folder.py --space DEV --title "API Documentation"
# Returns ID: 123456

# Create child folders
python create_confluence_folder.py --space DEV --title "REST API" --parent 123456
python create_confluence_folder.py --space DEV --title "GraphQL API" --parent 123456
```

### Create Folder with Description
```bash
python create_confluence_folder.py --space DEV --title "Archive" \
  --description "Historical documentation from previous versions"
```

### Create Using Parent Title
```bash
python create_confluence_folder.py --space DEV --title "Endpoints" \
  --parent-title "REST API"
```

## Error Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success - folder created |
| 1 | Error - space not found, parent not found, or API error |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CONFLUENCE_BASE_URL` | Yes | Confluence instance URL |
| `CONFLUENCE_EMAIL` | Yes | Atlassian account email |
| `CONFLUENCE_API_TOKEN` | Yes | API token from Atlassian account settings |

## Best Practices

1. **Consistent Naming**: Use clear, descriptive folder names
2. **Shallow Hierarchy**: Avoid deeply nested folder structures (3-4 levels max)
3. **Description**: Add descriptions to explain folder purpose
4. **Organization**: Group related content under common folders
