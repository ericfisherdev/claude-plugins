---
name: manage-sprint
description: This skill MUST be used when the user asks to "create sprint", "start sprint", "end sprint", "complete sprint", "close sprint", "new sprint", "begin sprint", "finish sprint", "update sprint", "rename sprint", or otherwise wants to create or change sprint state/details.
---

# Manage Sprint

Create, start, complete, and update sprints.

## Quick Start

Use the Python script at `scripts/manage_sprint.py`:

```bash
# Create a new 2-week sprint
python scripts/manage_sprint.py PROJ --create "Sprint 24" --duration 14

# Create sprint with specific dates
python scripts/manage_sprint.py PROJ --create "Sprint 24" \
  --start-date 2024-02-01 --end-date 2024-02-14

# Start a sprint (future -> active)
python scripts/manage_sprint.py PROJ --start --sprint-id 123

# Start the next future sprint
python scripts/manage_sprint.py PROJ --start --next

# Complete/close a sprint (active -> closed)
python scripts/manage_sprint.py PROJ --complete

# Complete specific sprint
python scripts/manage_sprint.py PROJ --complete --sprint-id 123
```

## Actions

| Action | Description |
|--------|-------------|
| `--create NAME` | Create new sprint with given name |
| `--start` | Start a sprint (future → active) |
| `--complete` | Complete a sprint (active → closed) |
| `--update` | Update sprint details |

## Create Options

| Option | Description |
|--------|-------------|
| `--create NAME` | Sprint name (required) |
| `--start-date DATE` | Start date (YYYY-MM-DD) |
| `--end-date DATE` | End date (YYYY-MM-DD) |
| `--duration DAYS` | Duration in days (default: 14) |
| `--goal TEXT` | Sprint goal |

If only `--duration` is provided, sprint starts tomorrow.

## Start/Complete Options

| Option | Description |
|--------|-------------|
| `--sprint-id ID` | Target specific sprint |
| `--next` | Start next future sprint |
| (none) | Start/complete uses next future / active sprint |

## Update Options

| Option | Description |
|--------|-------------|
| `--sprint-id ID` | Sprint to update (required) |
| `--name NAME` | New sprint name |
| `--start-date DATE` | New start date |
| `--end-date DATE` | New end date |
| `--goal TEXT` | New sprint goal |

## Examples

### Create and Start Sprint
```bash
# Create sprint starting tomorrow for 2 weeks
python scripts/manage_sprint.py PROJ --create "Sprint 24" --goal "Complete auth module"

# Start it immediately
python scripts/manage_sprint.py PROJ --start --next
```

### End Current Sprint
```bash
# Complete the active sprint
python scripts/manage_sprint.py PROJ --complete
```

### Update Sprint Details
```bash
# Rename and extend sprint
python scripts/manage_sprint.py PROJ --update --sprint-id 123 \
  --name "Sprint 24 (Extended)" --end-date 2024-02-21
```

## Output Example

### Compact (default)
```
CREATED|456|Sprint 24|future|2024-02-01|2024-02-14
```

```
STARTED|456|Sprint 24|active
```

```
COMPLETED|456|Sprint 24|closed
```

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Permissions

Requires "Manage Sprints" permission on the project's board.

## Reference

For complete options and error handling, see `references/options-reference.md`.
