# Sprint Info Options Reference

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `PROJECT` | Project key (required) | - |
| `--sprint-id ID` | Get specific sprint | Active sprint |
| `--list-sprints` | List all sprints | - |
| `--include-issues` | Include issue list | No |
| `--state STATE` | Filter: active, closed, future | All |
| `--format FORMAT` | compact, text, json | compact |
| `--refresh` | Force API refresh | Use cache |

## Output Formats

### Compact (default)
Most token-efficient. Pipe-delimited fields:
```
SPRINT|Sprint 23|active|2024-01-15|2024-01-29
PROGRESS|12/20 done|60%|8pts remaining
```

### Text
Human-readable multi-line format:
```
Sprint: Sprint 23
State: active
Start: 2024-01-15
End: 2024-01-29
Goal: Complete user authentication

Progress: 12/20 issues done (60%)
  In Progress: 5
  To Do: 3
Story Points: 21/34 (13 remaining)
```

### JSON
Structured data for programmatic use:
```json
{
  "sprint": {"id": 123, "name": "Sprint 23", "state": "active", ...},
  "progress": {"done": 12, "total": 20, "percentDone": 60, ...},
  "issues": [...]
}
```

## Sprint List Format

When using `--list-sprints`:

### Compact
```
*|123|Sprint 23|active|2024-01-15|2024-01-29
+|124|Sprint 24|future|2024-01-29|2024-02-12
-|122|Sprint 22|closed|2024-01-01|2024-01-15
```

State icons: `*` active, `+` future, `-` closed

### Text
```
Sprints:
  [*] 123: Sprint 23 (active)
      2024-01-15 - 2024-01-29
  [+] 124: Sprint 24 (future)
      2024-01-29 - 2024-02-12
```

## Progress Metrics

| Metric | Description |
|--------|-------------|
| `done` | Issues with status category "done" |
| `inProgress` | Issues with status category "indeterminate" |
| `todo` | Remaining issues |
| `percentDone` | Percentage of issues completed |
| `totalPoints` | Total story points in sprint |
| `donePoints` | Completed story points |
| `remainingPoints` | Story points remaining |

## Story Points

Story points are read from `customfield_10016` (the default Jira field). If your instance uses a different field, modify the script.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (no board, no sprint, API error) |

## Common Errors

| Error | Cause |
|-------|-------|
| "No board found" | Project doesn't have an agile board |
| "No active sprint" | No sprint is currently active |
| "Sprint not found" | Invalid sprint ID |
| "Access denied" | No permission to view board/sprint |

## Caching

Sprint and board information is cached:
- Board info: 24 hours
- Sprint metadata: 4 hours

Use `--refresh` to bypass cache.
