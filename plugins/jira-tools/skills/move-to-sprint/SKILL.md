---
name: move-to-sprint
description: This skill MUST be used when the user asks to "move issue to sprint", "add to sprint", "assign to sprint", "put in sprint", "add issue to current sprint", "move to backlog", "remove from sprint", or otherwise wants to change which sprint an issue belongs to.
---

# Move to Sprint

Move or add issues to a sprint, or remove them to backlog.

## Quick Start

Use the Python script at `scripts/move_to_sprint.py`:

```bash
# Move single issue to active sprint
python scripts/move_to_sprint.py PROJ-123

# Move multiple issues to active sprint
python scripts/move_to_sprint.py PROJ-123 PROJ-124 PROJ-125

# Move to specific sprint by ID
python scripts/move_to_sprint.py PROJ-123 --sprint-id 456

# Move to backlog (remove from sprint)
python scripts/move_to_sprint.py PROJ-123 --backlog

# Move to next upcoming sprint
python scripts/move_to_sprint.py PROJ-123 --next-sprint
```

## Options

| Option | Description |
|--------|-------------|
| `ISSUES` | One or more issue keys (required) |
| `--sprint-id ID` | Target sprint ID |
| `--backlog` | Move to backlog (remove from sprint) |
| `--next-sprint` | Move to next future sprint |
| `--list-sprints` | List available sprints |
| `--format FORMAT` | Output: compact (default), text, json |

## Common Workflows

### Add to Current Sprint
```bash
# Move new issues to the active sprint
python scripts/move_to_sprint.py PROJ-101 PROJ-102 PROJ-103
```

### Move to Next Sprint
```bash
# Defer issues to next planned sprint
python scripts/move_to_sprint.py PROJ-101 --next-sprint
```

### Return to Backlog
```bash
# Remove from sprint, return to backlog
python scripts/move_to_sprint.py PROJ-101 --backlog
```

### Move to Specific Sprint
```bash
# First, list available sprints
python scripts/move_to_sprint.py PROJ-101 --list-sprints

# Then move to chosen sprint
python scripts/move_to_sprint.py PROJ-101 --sprint-id 456
```

## Output Example

### Compact (default)
```
MOVED|PROJ-123,PROJ-124|Sprint 23
```

### Text
```
Moved 2 issues to Sprint 23:
  PROJ-123: Implement login
  PROJ-124: Fix validation bug
```

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Permissions

Requires "Schedule Issues" permission on the project's board.

## Reference

For complete options and error handling, see `references/options-reference.md`.
