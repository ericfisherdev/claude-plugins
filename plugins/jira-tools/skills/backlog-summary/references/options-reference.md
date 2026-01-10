# Backlog Summary Options Reference

Complete reference for the backlog-summary skill script options.

## Command Line Arguments

### Required Arguments

| Argument | Description |
|----------|-------------|
| `project` | Jira project key (e.g., `EFT`, `PROJ`) |

### Scope Options

| Flag | Default | Description |
|------|---------|-------------|
| `--scope SCOPE` | `all` | Filter by sprint scope: `all`, `backlog`, `active-sprint`, `past-sprints` |

**Scope Details:**

| Scope | JQL Generated | Cache Category | TTL |
|-------|---------------|----------------|-----|
| `all` | (none) | Auto-detected | Varies |
| `backlog` | `Sprint is EMPTY` | `issues_backlog` | 12 hours |
| `active-sprint` | `Sprint in openSprints()` | `issues_active_sprint` | 1 hour |
| `past-sprints` | `Sprint in closedSprints()` | `issues_past_sprints` | 24 hours |

### Filter Options

| Flag | Short | Description |
|------|-------|-------------|
| `--label LABEL` | `-l` | Include only issues with this label. Can be repeated. |
| `--exclude-label LABEL` | `-L` | Exclude issues with this label. Can be repeated. |
| `--status STATUS` | `-s` | Include only issues with this status. Can be repeated. |
| `--exclude-status STATUS` | `-S` | Exclude issues with this status. Can be repeated. |
| `--jql JQL` | `-q` | Additional JQL clause to append to the query. |

### Output Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--max-results COUNT` | `-n` | 50 | Maximum number of issues to retrieve. |
| `--format FORMAT` | `-f` | compact | Output format: `compact`, `json`, `text`. |

### Cache Options

| Flag | Description |
|------|-------------|
| `--no-cache` | Don't cache results to shared cache file. |
| `--refresh` | Force refresh, ignoring any cached results. |

### Discovery Options

| Flag | Description |
|------|-------------|
| `--list-statuses` | List available statuses for the project and exit. |
| `--list-labels` | List available labels and exit. |
| `--list-sprints` | List sprints for the project (active, future, closed) and exit. |

## Filter Examples

### Label Filters

```bash
# Issues with the "vue" label
python scripts/fetch_backlog.py EFT --label vue

# Issues with both "vue" AND "urgent" labels
python scripts/fetch_backlog.py EFT --label vue --label urgent

# Issues without the "legacy" label
python scripts/fetch_backlog.py EFT --exclude-label legacy

# Vue issues excluding legacy
python scripts/fetch_backlog.py EFT --label vue --exclude-label legacy
```

### Status Filters

```bash
# Only "Open" issues
python scripts/fetch_backlog.py EFT --status Open

# "Open" or "To Do" issues
python scripts/fetch_backlog.py EFT --status Open --status "To Do"

# Everything except "Done"
python scripts/fetch_backlog.py EFT --exclude-status Done

# Not in progress or done
python scripts/fetch_backlog.py EFT --exclude-status "In Progress" --exclude-status Done
```

### Combined Filters

```bash
# Vue frontend issues that aren't done
python scripts/fetch_backlog.py EFT --label vue --label frontend --exclude-status Done

# High priority open items
python scripts/fetch_backlog.py EFT --status Open --jql "priority = High"
```

### Custom JQL

```bash
# Assigned to current user
python scripts/fetch_backlog.py EFT --jql "assignee = currentUser()"

# Created in last 7 days
python scripts/fetch_backlog.py EFT --jql "created >= -7d"

# Unassigned issues
python scripts/fetch_backlog.py EFT --jql "assignee is EMPTY"

# Issues with components
python scripts/fetch_backlog.py EFT --jql 'component = "Frontend"'
```

## Output Formats

### Compact Format (Default)

Ultra-minimal token usage. One line per issue:

```
EFT-123|Open|vue,frontend|Implement dark mode toggle
EFT-124|In Progress|-|Fix login validation
EFT-125|To Do|backend,api|Add rate limiting
```

**Format:** `KEY|status|labels|summary`
- Labels are comma-separated
- `-` indicates no labels

### JSON Format

Compact JSON array:

```json
[{"id":"10001","key":"EFT-123","summary":"Implement dark mode toggle","status":"Open","labels":["vue","frontend"]},{"id":"10002","key":"EFT-124","summary":"Fix login validation","status":"In Progress","labels":[]}]
```

### Text Format

Human-readable multi-line:

```
EFT-123: Implement dark mode toggle
  Status: Open | Labels: vue, frontend

EFT-124: Fix login validation
  Status: In Progress | Labels: none

EFT-125: Add rate limiting
  Status: To Do | Labels: backend, api
```

## Sprint-Aware Caching

Issues are cached in three separate categories with different TTLs:

### Cache Categories

| Category | Cache Key | TTL | Use Case |
|----------|-----------|-----|----------|
| Active Sprint | `issues_active_sprint` | 1 hour | Issues change frequently during active sprints |
| Backlog | `issues_backlog` | 12 hours | Backlog items change less frequently |
| Past Sprints | `issues_past_sprints` | 24 hours | Closed sprint issues rarely change |

### Cached Issue Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Internal Jira issue ID |
| `key` | string | Issue key (e.g., `EFT-123`) |
| `summary` | string | Issue summary/title |
| `status` | string | Current status name |
| `labels` | array | List of label strings |
| `sprint` | object | Sprint info for categorization (optional) |
| `_cached_at` | string | ISO timestamp when cached |
| `_category` | string | Cache category (active_sprint, backlog, past_sprints) |

### Cache Management Commands

```bash
# View all cache info
python shared/jira_cache.py info

# Clear all issue caches
python shared/jira_cache.py clear-issues

# Clear specific category
python shared/jira_cache.py clear-issues --category backlog
python shared/jira_cache.py clear-issues --category active_sprint
python shared/jira_cache.py clear-issues --category past_sprints

# Clear for specific project
python shared/jira_cache.py clear-issues -p EFT

# Clear specific project + category
python shared/jira_cache.py clear-issues -p EFT --category active_sprint

# Move sprint issues to past_sprints when sprint closes
python shared/jira_cache.py close-sprint -p EFT --sprint-id 123

# List sprints for a project
python shared/jira_cache.py sprints -p EFT
```

Other jira-tools skills (update-issue, jira-issue) will update cached fields when they modify or fetch issues, automatically moving issues between categories when sprint status changes.

## Error Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | Error (environment, JQL, permission, connection) |

## Common JQL Operators

For use with `--jql`:

| Operator | Example | Description |
|----------|---------|-------------|
| `=` | `priority = High` | Equals |
| `!=` | `status != Done` | Not equals |
| `IN` | `status IN (Open, "To Do")` | In list |
| `NOT IN` | `labels NOT IN (legacy)` | Not in list |
| `IS EMPTY` | `assignee IS EMPTY` | Field is empty |
| `IS NOT EMPTY` | `labels IS NOT EMPTY` | Field has value |
| `~` | `summary ~ "bug"` | Contains text |
| `>=` | `created >= -7d` | Greater than or equal |
| `<=` | `updated <= -30d` | Less than or equal |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_BASE_URL` | Yes | Jira instance URL (e.g., `https://yoursite.atlassian.net`) |
| `JIRA_EMAIL` | Yes | User email for authentication |
| `JIRA_API_TOKEN` | Yes | API token from Atlassian account settings |
