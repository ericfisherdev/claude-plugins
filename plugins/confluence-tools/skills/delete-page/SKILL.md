---
name: delete-page
description: This skill MUST be used when the user asks to "delete a Confluence page", "remove a page", "delete a folder", "remove content from wiki", or wants to delete pages or folders from Confluence. ALWAYS use this skill for Confluence content deletion.
---

# Delete Confluence Page or Folder

**IMPORTANT:** Always use this skill's Python script for deleting Confluence pages and folders. This skill auto-detects content type and handles both pages and folders.

## Quick Start

Use the Python script at `scripts/delete_confluence_page.py`:

```bash
# Delete a page (auto-detect type)
python scripts/delete_confluence_page.py --id 123456

# Delete a folder explicitly
python scripts/delete_confluence_page.py --id 123456 --type folder

# Delete a page explicitly
python scripts/delete_confluence_page.py --id 123456 --type page
```

## Options

| Option | Description |
|--------|-------------|
| `--id`, `-i` | Page or folder ID to delete (required) |
| `--type`, `-t` | Content type: page, folder, auto (default: auto) |
| `--format`, `-f` | Output: compact (default), text, json |

## Important Notes

1. **Children must be deleted first** - You cannot delete a page or folder that has children. Delete the children first, or delete recursively starting from the deepest level.

2. **Deletion is permanent** - Deleted content goes to the trash but should be treated as permanent. Use with caution.

3. **Auto-detection** - By default, the script tries to find the content as a page first, then as a folder. Use `--type` to skip auto-detection if you know the type.

## Common Workflows

### Delete a Single Page
```bash
python scripts/delete_confluence_page.py --id 123456
```

### Delete a Folder Structure (Bottom-Up)
When deleting a folder hierarchy, delete children first:

```bash
# First delete all pages in the folder
python scripts/delete_confluence_page.py --id 123459  # Child page 1
python scripts/delete_confluence_page.py --id 123460  # Child page 2

# Then delete the folder itself
python scripts/delete_confluence_page.py --id 123458 --type folder
```

### Delete Multiple Pages
```bash
# Delete several pages
for id in 123456 123457 123458; do
  python scripts/delete_confluence_page.py --id $id
done
```

## Output Formats

**compact** (default):
```
DELETED|123456|page|My Page Title
```

**text**:
```
Deleted: My Page Title
ID: 123456
Type: page
```

**json**:
```json
{"id": "123456", "title": "My Page Title", "type": "page", "deleted": true}
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "not found" | ID doesn't exist | Verify the ID is correct |
| "has children" | Content has child pages | Delete children first |
| "permission denied" | No delete permission | Check your permissions |

## Environment Setup

Requires environment variables:
- `CONFLUENCE_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `CONFLUENCE_EMAIL` - Your Atlassian account email
- `CONFLUENCE_API_TOKEN` - API token from Atlassian account settings
