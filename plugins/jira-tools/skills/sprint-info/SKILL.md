---
name: sprint-info
description: This skill MUST be used when the user asks to "get sprint info", "show sprint details", "what's in the sprint", "sprint status", "current sprint", "active sprint details", "list sprint issues", "sprint progress", or needs information about a specific sprint. Use this for sprint-level details - use backlog-summary for bulk issue listing across sprints.
---

# Sprint Info

View detailed sprint information including issues, progress, and dates.

## Quick Start

Use the Python script at `scripts/sprint_info.py`:

```bash
# Get active sprint info for project
python scripts/sprint_info.py PROJ

# Get specific sprint by ID
python scripts/sprint_info.py PROJ --sprint-id 123

# List all sprints for project
python scripts/sprint_info.py PROJ --list-sprints

# Get sprint with issue details
python scripts/sprint_info.py PROJ --include-issues
```

## Options

| Option | Description |
|--------|-------------|
| `--sprint-id ID` | Get specific sprint (default: active sprint) |
| `--list-sprints` | List all sprints for project |
| `--include-issues` | Include issue list in output |
| `--state STATE` | Filter sprints: active, closed, future |
| `--format FORMAT` | Output: compact (default), text, json |

## Output Examples

### Compact (default)
```
SPRINT|Sprint 23|active|2024-01-15|2024-01-29
PROGRESS|12/20 done|60%|8 story points remaining
```

### With Issues
```
SPRINT|Sprint 23|active|2024-01-15|2024-01-29
PROGRESS|12/20 done|60%|8 story points remaining
ISSUES:
PROJ-101|Done|Implement login
PROJ-102|In Progress|Fix validation bug
PROJ-103|To Do|Add dark mode
```

## Sprint States

| State | Description |
|-------|-------------|
| `active` | Currently running sprint |
| `future` | Planned/upcoming sprint |
| `closed` | Completed sprint |

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Shared Cache

This skill uses the shared Jira cache (`~/.jira-tools-cache.json`) for:
- Board information
- Sprint metadata
- Issue data

Sprint info is cached for 4 hours. Use `--refresh` to force update.

## Reference

For complete options, see `references/options-reference.md`.
