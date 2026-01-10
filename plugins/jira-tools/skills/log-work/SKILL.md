---
name: log-work
description: This skill MUST be used when the user asks to "log work", "log time", "add worklog", "track time", "record hours", "time tracking", "log 2 hours", or otherwise requests adding time entries to Jira issues.
---

# Log Work on Jira Issues

Add worklogs to track time spent on Jira issues.

## Quick Start

Use the Python script at `scripts/log_work.py`:

```bash
# Log 2 hours of work
python scripts/log_work.py PROJ-123 --time "2h"

# Log time with a comment
python scripts/log_work.py PROJ-123 --time "1h 30m" --comment "Code review and testing"

# Log work for a specific date
python scripts/log_work.py PROJ-123 --time "3h" --started "2024-01-15T09:00:00"

# Log work and adjust remaining estimate
python scripts/log_work.py PROJ-123 --time "4h" --adjust-estimate auto
```

## Required Arguments

| Argument | Description |
|----------|-------------|
| `issue_key` | Issue key (e.g., PROJ-123) |
| `--time`, `-t` | Time spent (e.g., "2h", "1h 30m", "90m") |

## Optional Arguments

| Argument | Description |
|----------|-------------|
| `--comment`, `-c` | Description of work done |
| `--started`, `-s` | Start date/time (ISO format, default: now) |
| `--adjust-estimate` | How to adjust remaining: auto, leave, new, manual |
| `--new-estimate` | New remaining estimate (with --adjust-estimate new) |
| `--reduce-by` | Reduce remaining by this amount (with --adjust-estimate manual) |
| `--format`, `-f` | Output: compact (default), text, json |

## Time Format

Time can be specified in Jira format:
- `2h` - 2 hours
- `30m` - 30 minutes
- `1h 30m` - 1 hour and 30 minutes
- `1d` - 1 day (typically 8 hours)
- `1w` - 1 week (typically 5 days)

## Examples

### Simple Time Log
```bash
python scripts/log_work.py PROJ-123 --time "2h"
```

### Log with Description
```bash
python scripts/log_work.py PROJ-123 --time "4h" --comment "Implemented authentication flow"
```

### Log Past Work
```bash
python scripts/log_work.py PROJ-123 --time "3h" \
  --started "2024-01-10T14:00:00" \
  --comment "Bug investigation from last week"
```

### Adjust Remaining Estimate
```bash
# Automatically reduce remaining estimate
python scripts/log_work.py PROJ-123 --time "2h" --adjust-estimate auto

# Set a new remaining estimate
python scripts/log_work.py PROJ-123 --time "2h" --adjust-estimate new --new-estimate "4h"

# Don't change remaining estimate
python scripts/log_work.py PROJ-123 --time "2h" --adjust-estimate leave
```

## Output Formats

**compact** (default):
```
LOGGED|PROJ-123|2h|@jsmith|2024-01-15
```

**text**:
```
Work Logged
Issue: PROJ-123
Time: 2h (7200 seconds)
Author: John Smith
Started: 2024-01-15T09:00:00
Comment: Code review and testing
```

**json**:
```json
{"issue":"PROJ-123","timeSpent":"2h","timeSpentSeconds":7200,"started":"2024-01-15T09:00:00"}
```

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Prerequisites

Time tracking must be enabled in your Jira project settings. The user must have "Work on Issues" permission.

## Reference

For detailed options and error codes, see `references/options-reference.md`.
