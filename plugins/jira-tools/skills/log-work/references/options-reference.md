# Log Work Options Reference

## Time Format

| Format | Meaning | Seconds |
|--------|---------|---------|
| `1w` | 1 week (5 work days) | 144000 |
| `1d` | 1 day (8 hours) | 28800 |
| `1h` | 1 hour | 3600 |
| `1m` | 1 minute | 60 |
| `1h 30m` | 1.5 hours | 5400 |
| `2d 4h` | 2 days 4 hours | 72000 |

## Estimate Adjustment Options

| Option | Description |
|--------|-------------|
| `auto` | Automatically reduce remaining estimate by time logged |
| `leave` | Don't change the remaining estimate |
| `new` | Set a new remaining estimate (requires --new-estimate) |
| `manual` | Reduce remaining by specific amount (requires --reduce-by) |

### Examples

```bash
# Auto-reduce remaining estimate
python log_work.py PROJ-123 --time "2h" --adjust-estimate auto

# Keep remaining estimate unchanged
python log_work.py PROJ-123 --time "2h" --adjust-estimate leave

# Set new remaining estimate to 4 hours
python log_work.py PROJ-123 --time "2h" --adjust-estimate new --new-estimate "4h"

# Manually reduce remaining by 1 hour
python log_work.py PROJ-123 --time "2h" --adjust-estimate manual --reduce-by "1h"
```

## Date/Time Format

The `--started` parameter accepts ISO 8601 format:

```
2024-01-15T09:00:00.000+0000
2024-01-15T14:30:00
2024-01-15
```

If only a date is provided, time defaults to start of day.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid input, API error, permission denied) |

## Common Errors

| Error | Cause |
|-------|-------|
| "Time tracking is not enabled" | Enable time tracking in project settings |
| "Issue not found" | Invalid issue key |
| "Access denied" | No "Work on Issues" permission |
| "Invalid time format" | Unrecognized time string |

## Prerequisites

1. Time tracking must be enabled in Jira project settings
2. User must have "Work on Issues" permission
3. User must have "Browse Projects" permission
