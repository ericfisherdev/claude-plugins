# Link Issues Options Reference

## Standard Jira Link Types

| Name | Outward Description | Inward Description |
|------|--------------------|--------------------|
| Blocks | blocks | is blocked by |
| Cloners | clones | is cloned by |
| Duplicate | duplicates | is duplicated by |
| Relates | relates to | relates to |

Note: Your Jira instance may have additional custom link types. Use `--list-types` to see all available options.

## Link Direction

When creating a link:
- **Outward issue**: The issue that performs the action (e.g., "PROJ-100 blocks...")
- **Inward issue**: The issue that receives the action (e.g., "...is blocked by PROJ-100")

Example: `link_issues.py PROJ-100 PROJ-101 --type Blocks`
- PROJ-100 will show "blocks PROJ-101"
- PROJ-101 will show "is blocked by PROJ-100"

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid input, API error, permission denied) |

## Error Messages

| Error | Cause |
|-------|-------|
| "Link type not found" | Invalid link type name |
| "Resource not found" | One or both issue keys don't exist |
| "Access denied" | No permission to link issues |
| "Authentication failed" | Invalid credentials |
