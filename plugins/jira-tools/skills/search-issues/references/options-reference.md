# Search Issues Options Reference

## JQL Syntax

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `status = "In Progress"` |
| `!=` | Not equals | `status != Done` |
| `>` | Greater than | `priority > Medium` |
| `<` | Less than | `created < "2024-01-01"` |
| `>=` | Greater or equal | `created >= -7d` |
| `<=` | Less or equal | `updated <= -1d` |
| `~` | Contains (text) | `summary ~ "login"` |
| `!~` | Not contains | `summary !~ "test"` |

### Logical Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `AND` | Both conditions | `project = A AND status = Open` |
| `OR` | Either condition | `type = Bug OR type = Task` |
| `NOT` | Negate | `NOT status = Done` |

### Special Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `in` | In list | `status in (Open, "In Progress")` |
| `not in` | Not in list | `priority not in (Low, Lowest)` |
| `is` | Is null/empty | `assignee is EMPTY` |
| `is not` | Is not null | `assignee is not EMPTY` |
| `was` | Previous value | `status was "In Progress"` |
| `changed` | Field changed | `status changed` |

### Date Functions

| Function | Description | Example |
|----------|-------------|---------|
| `now()` | Current time | `created < now()` |
| `startOfDay()` | Start of today | `created >= startOfDay()` |
| `startOfWeek()` | Start of week | `created >= startOfWeek()` |
| `startOfMonth()` | Start of month | `created >= startOfMonth()` |
| `endOfDay()` | End of today | `due <= endOfDay()` |
| `-7d` | Relative days | `created >= -7d` |
| `-2w` | Relative weeks | `updated >= -2w` |

### User Functions

| Function | Description | Example |
|----------|-------------|---------|
| `currentUser()` | Logged-in user | `assignee = currentUser()` |
| `membersOf("group")` | Group members | `assignee in membersOf("dev-team")` |

### Sprint Functions

| Function | Description |
|----------|-------------|
| `openSprints()` | Active sprints |
| `closedSprints()` | Completed sprints |
| `futureSprints()` | Planned sprints |

## Common JQL Queries

### Find My Work
```
assignee = currentUser() AND resolution = Unresolved
```

### Open Bugs
```
project = PROJ AND type = Bug AND status not in (Done, Closed)
```

### Recently Updated
```
project = PROJ AND updated >= -24h ORDER BY updated DESC
```

### High Priority
```
priority in (Critical, Highest, High) AND resolution = Unresolved
```

### Text Search
```
text ~ "error handling" AND project = PROJ
```

### Sprint Work
```
project = PROJ AND sprint in openSprints()
```

### Overdue Issues
```
project = PROJ AND due < now() AND resolution = Unresolved
```

## Available Fields

Common fields for `--fields` parameter:

- `summary` - Issue title
- `status` - Current status
- `issuetype` - Issue type
- `priority` - Priority level
- `assignee` - Assigned user
- `reporter` - Issue creator
- `created` - Creation date
- `updated` - Last update date
- `labels` - Issue labels
- `components` - Components
- `description` - Full description
- `fixVersions` - Fix versions
- `resolution` - Resolution status

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid JQL, permission denied, etc.) |

## Limits

- Default max results: 20
- Maximum allowed: 100 (API limit)
- For more results, use pagination or refine query
