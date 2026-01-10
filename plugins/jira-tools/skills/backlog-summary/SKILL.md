---
name: backlog-summary
description: This skill MUST be used when the user asks to "get backlog", "list backlog issues", "show backlog", "what's in the backlog", "backlog summary", "list Jira issues", "show issues in project", "what issues are pending", "show sprint issues", "active sprint", "past sprints", or needs a quick overview of multiple issues. Use this for bulk issue listing - use jira-issue for single issue details.
---

# Jira Backlog Summary

Fetch a token-efficient summary of issues from Jira with sprint-aware caching. Returns only essential fields: issue key, status, labels, and summary.

## Quick Start

Use the Python script at `scripts/fetch_backlog.py`:

```bash
# Get all issues in project (default 50)
python scripts/fetch_backlog.py EFT

# Get only backlog issues (not in any sprint)
python scripts/fetch_backlog.py EFT --scope backlog

# Get active sprint issues
python scripts/fetch_backlog.py EFT --scope active-sprint

# Get issues from past/closed sprints
python scripts/fetch_backlog.py EFT --scope past-sprints
```

## Scope Options

| Scope | Description | Cache TTL |
|-------|-------------|-----------|
| `all` (default) | All issues | Auto-categorized |
| `backlog` | Issues not in any sprint | 12 hours |
| `active-sprint` | Issues in current sprint | 1 hour |
| `past-sprints` | Issues from closed sprints | 24 hours |

## Filter Examples

### Scope + Label Filters

```bash
# Backlog Vue issues
python scripts/fetch_backlog.py EFT --scope backlog --label vue

# Active sprint excluding legacy
python scripts/fetch_backlog.py EFT --scope active-sprint --exclude-label legacy

# Past sprint issues that are done
python scripts/fetch_backlog.py EFT --scope past-sprints --status Done
```

### Status Filters

```bash
# Only open backlog issues
python scripts/fetch_backlog.py EFT --scope backlog --status Open --status "To Do"

# Active sprint, not done
python scripts/fetch_backlog.py EFT --scope active-sprint --exclude-status Done
```

## Output Formats

### Compact (default)
Most token-efficient. One line per issue:
```
EFT-123|Open|vue,frontend|Implement dark mode toggle
EFT-124|In Progress|-|Fix login validation
```
Format: `KEY|status|labels|summary` (labels `-` if none)

### JSON
```bash
python scripts/fetch_backlog.py EFT --format json
```
Returns compact JSON array for programmatic use.

### Text
```bash
python scripts/fetch_backlog.py EFT --format text
```
Multi-line human-readable format.

## Sprint-Aware Caching

Issues are cached in three categories with different TTLs:

| Category | TTL | Use Case |
|----------|-----|----------|
| `active_sprint` | 1 hour | Issues change frequently during active sprints |
| `backlog` | 12 hours | Backlog items change less frequently |
| `past_sprints` | 24 hours | Closed sprint issues rarely change |

### Cache Management

```bash
# View cache status
python shared/jira_cache.py info

# Clear all issue cache
python shared/jira_cache.py clear-issues

# Clear only backlog cache
python shared/jira_cache.py clear-issues --category backlog

# Clear only active sprint cache for project
python shared/jira_cache.py clear-issues -p EFT --category active_sprint

# Move issues to past_sprints when sprint closes
python shared/jira_cache.py close-sprint -p EFT --sprint-id 123
```

## Discovery Commands

List available filter values:

```bash
# List sprints for project
python scripts/fetch_backlog.py EFT --list-sprints

# List statuses for project
python scripts/fetch_backlog.py EFT --list-statuses

# List available labels
python scripts/fetch_backlog.py EFT --list-labels
```

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Token Efficiency

This skill is optimized for minimal token usage:
- Only fetches: key, status, labels, summary (no description, comments, etc.)
- Compact output uses pipe delimiters
- Default limit of 50 issues prevents oversized responses
- Sprint-aware caching reduces API calls

For detailed single-issue information, use the `jira-issue` skill instead.

## Reference

For complete filter options and JQL examples, see `references/options-reference.md`.
