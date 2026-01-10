---
name: watch-issue
description: This skill MUST be used when the user asks to "watch issue", "add watcher", "remove watcher", "stop watching", "follow issue", "unfollow issue", "subscribe to issue", or otherwise requests managing watchers on Jira issues.
---

# Watch Jira Issues

Add or remove watchers from Jira issues to receive notifications about updates.

## Quick Start

Use the Python script at `scripts/watch_issue.py`:

```bash
# Watch an issue (add yourself)
python scripts/watch_issue.py PROJ-123 --watch

# Stop watching an issue
python scripts/watch_issue.py PROJ-123 --unwatch

# Add another user as watcher
python scripts/watch_issue.py PROJ-123 --add "John Smith"

# Remove a watcher
python scripts/watch_issue.py PROJ-123 --remove "John Smith"

# List current watchers
python scripts/watch_issue.py PROJ-123 --list
```

## Arguments

| Argument | Description |
|----------|-------------|
| `issue_key` | Issue key (e.g., PROJ-123) |
| `--watch`, `-w` | Add yourself as a watcher |
| `--unwatch`, `-u` | Remove yourself as a watcher |
| `--add`, `-a` | Add a user as watcher (by name) |
| `--remove`, `-r` | Remove a user as watcher (by name) |
| `--list`, `-l` | List current watchers |
| `--format`, `-f` | Output: compact (default), text, json |

## Examples

### Watch an Issue
```bash
python scripts/watch_issue.py PROJ-123 --watch
```

### Stop Watching
```bash
python scripts/watch_issue.py PROJ-123 --unwatch
```

### Add Team Member as Watcher
```bash
python scripts/watch_issue.py PROJ-123 --add "Jane Doe"
```

### List All Watchers
```bash
python scripts/watch_issue.py PROJ-123 --list
```

### Multiple Operations
```bash
# Add yourself and list watchers
python scripts/watch_issue.py PROJ-123 --watch --list
```

## Output Formats

**compact** (default):
```
WATCHED|PROJ-123|added|@jsmith
```

```
WATCHERS|PROJ-123|3|@jsmith,@jdoe,@alice
```

**text**:
```
Watcher Added
Issue: PROJ-123
User: John Smith
Total Watchers: 3
```

```
Watchers for PROJ-123:
- John Smith
- Jane Doe
- Alice Brown
Total: 3 watchers
```

**json**:
```json
{"issue":"PROJ-123","action":"added","user":"John Smith","watchCount":3}
```

```json
{"issue":"PROJ-123","watchers":["John Smith","Jane Doe"],"count":2}
```

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Prerequisites

- "Allow users to watch issues" must be enabled in Jira settings
- User must have "Browse Projects" permission
- User must have "Manage Watcher List" permission to add/remove other users

## Reference

For detailed options, see `references/options-reference.md`.
