# Watch Issue Options Reference

## Actions

| Action | Description |
|--------|-------------|
| `--watch` | Add yourself as a watcher |
| `--unwatch` | Remove yourself as a watcher |
| `--add USER` | Add another user as watcher |
| `--remove USER` | Remove another user as watcher |
| `--list` | Show all current watchers |

## User Lookup

When using `--add` or `--remove`, you can specify users by:
- Full name: `"John Smith"`
- Partial name: `"John"` (matches first user containing "John")

The script uses the shared cache when available for faster lookups.

## Multiple Operations

You can combine multiple actions in one command:

```bash
# Add yourself and list watchers
python watch_issue.py PROJ-123 --watch --list

# Add multiple users (run twice)
python watch_issue.py PROJ-123 --add "John"
python watch_issue.py PROJ-123 --add "Jane"
```

## Permissions

| Permission | Required For |
|------------|--------------|
| Browse Projects | View watchers |
| Manage Watcher List | Add/remove other users |
| - | Add/remove yourself (always allowed) |

Note: The "Allow users to watch issues" option must be enabled in Jira settings.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (issue not found, user not found, permission denied) |

## Common Errors

| Error | Cause |
|-------|-------|
| "Issue not found" | Invalid issue key |
| "User not found" | No user matches the name |
| "Access denied" | No permission to manage watchers |
| "Watching is disabled" | Admin has disabled issue watching |

## Watcher Limits

Jira may limit the number of watchers per issue (configurable by admin). If you receive an error when adding watchers, check with your Jira administrator.
