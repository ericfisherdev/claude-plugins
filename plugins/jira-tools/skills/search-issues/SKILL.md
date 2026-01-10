---
name: search-issues
description: This skill MUST be used when the user asks to "search issues", "find issues", "JQL search", "query Jira", "list issues matching", "find tickets where", "search for bugs", "find my issues", or otherwise requests searching for Jira issues using criteria or JQL.
---

# Search Jira Issues with JQL

Search for Jira issues using JQL (Jira Query Language) or simple filters.

## Quick Start

Use the Python script at `scripts/search_issues.py`:

```bash
# Simple project search
python scripts/search_issues.py --project PROJ

# JQL query
python scripts/search_issues.py --jql "project = PROJ AND status = 'In Progress'"

# Quick filters
python scripts/search_issues.py --project PROJ --status "Open" --assignee "John"

# My open issues
python scripts/search_issues.py --jql "assignee = currentUser() AND resolution = Unresolved"
```

## Query Options

| Argument | Description |
|----------|-------------|
| `--jql`, `-q` | Raw JQL query string |
| `--project`, `-p` | Filter by project key |
| `--status`, `-s` | Filter by status name |
| `--assignee`, `-a` | Filter by assignee (name or "me") |
| `--type`, `-t` | Filter by issue type (Bug, Story, etc.) |
| `--priority` | Filter by priority |
| `--labels`, `-l` | Filter by labels (comma-separated) |
| `--created` | Created date filter (e.g., "-7d", "2024-01-01") |
| `--updated` | Updated date filter |

## Output Options

| Argument | Description |
|----------|-------------|
| `--max-results`, `-n` | Maximum results (default: 20) |
| `--fields` | Fields to retrieve (comma-separated) |
| `--format`, `-f` | Output: compact (default), text, json, table |
| `--order` | Sort order (e.g., "created DESC") |

## JQL Quick Reference

### Common Queries

```bash
# All open bugs in a project
--jql "project = PROJ AND type = Bug AND resolution = Unresolved"

# My issues updated this week
--jql "assignee = currentUser() AND updated >= -7d"

# High priority issues
--jql "priority in (Critical, High) AND status != Done"

# Issues with specific labels
--jql "labels in (backend, api)"

# Recently created issues
--jql "project = PROJ AND created >= -24h"

# Issues in current sprint
--jql "project = PROJ AND sprint in openSprints()"
```

### JQL Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `status = "In Progress"` |
| `!=` | Not equals | `status != Done` |
| `~` | Contains | `summary ~ "login"` |
| `in` | In list | `status in (Open, "In Progress")` |
| `is` | Is null | `assignee is EMPTY` |
| `>=`, `<=` | Comparison | `created >= -7d` |

## Examples

### Find Open Bugs
```bash
python scripts/search_issues.py \
  --project PROJ \
  --type Bug \
  --status Open
```

### Search by Text
```bash
python scripts/search_issues.py \
  --jql "project = PROJ AND (summary ~ 'login' OR description ~ 'login')"
```

### My Assigned Issues
```bash
python scripts/search_issues.py \
  --assignee me \
  --status "In Progress" \
  --order "priority DESC"
```

### Issues Updated Recently
```bash
python scripts/search_issues.py \
  --project PROJ \
  --updated "-2d" \
  --max-results 50
```

## Output Formats

**compact** (default):
```
PROJ-123|Fix login bug|In Progress|Bug|P:High|@jsmith
PROJ-124|Update docs|Open|Task|P:Medium|@jdoe
Found: 2 issues
```

**table**:
```
Key       | Summary              | Status      | Type | Priority | Assignee
----------|----------------------|-------------|------|----------|----------
PROJ-123  | Fix login bug        | In Progress | Bug  | High     | jsmith
PROJ-124  | Update docs          | Open        | Task | Medium   | jdoe
```

**text**:
```
Issue: PROJ-123
Summary: Fix login bug
Status: In Progress
Type: Bug
Priority: High
Assignee: John Smith
---
Issue: PROJ-124
...
```

**json**:
```json
{"total":2,"issues":[{"key":"PROJ-123","summary":"Fix login bug",...}]}
```

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Reference

For JQL syntax and field reference, see `references/options-reference.md`.
