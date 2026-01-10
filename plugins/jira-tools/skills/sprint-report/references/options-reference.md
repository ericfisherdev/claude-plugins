# Sprint Report Options Reference

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `PROJECT` | Project key (required) | - |
| `--sprint-id ID` | Report for specific sprint | Active sprint |
| `--detailed` | Include issue breakdown | No |
| `--velocity` | Include velocity metrics | No |
| `--format FORMAT` | compact, text, json | compact |

## Metrics Explained

### Issue Counts

| Metric | Description |
|--------|-------------|
| `done` | Issues with status category "Done" |
| `inProgress` | Issues with status category "In Progress" |
| `todo` | Issues with status category "To Do" |
| `percentDone` | Percentage of issues completed |

### Story Points

| Metric | Description |
|--------|-------------|
| `totalPoints` | Sum of story points for all sprint issues |
| `donePoints` | Sum of story points for completed issues |
| `remainingPoints` | Points still to complete |

Note: Story points are read from `customfield_10016` (common default).

### Velocity

| Metric | Description |
|--------|-------------|
| `current` | Total points planned for current sprint |
| `average` | Average completed points from last 3 sprints |
| `trend` | Direction: up, down, stable |
| `history` | Points completed in recent sprints |

## Output Formats

### Compact (default)
```
SPRINT|Sprint 23|active|2024-01-15|2024-01-29|60%
ISSUES|12/20 done|5 in-progress|3 todo
POINTS|21/34|13 remaining
VELOCITY|34|avg:32|trend:^
```

Trend symbols: `^` up, `v` down, `-` stable

### With --detailed
```
SPRINT|Sprint 23|active|2024-01-15|2024-01-29|60%
ISSUES|12/20 done|5 in-progress|3 todo
POINTS|21/34|13 remaining
BY_STATUS|Done:12|In Progress:5|To Do:3
BY_TYPE|Story:10|Bug:6|Task:4
REMAINING:
  PROJ-101|In Progress|@john|Implement login(3pts)
  PROJ-102|To Do|unassigned|Fix validation(2pts)
```

### Text
Human-readable multi-line format with sections for:
- Sprint info
- Progress summary
- Story points
- Velocity (if --velocity)
- Breakdowns (if --detailed)

### JSON
Full structured data for programmatic use.

## Velocity Calculation

Velocity trend is calculated by comparing the most recent closed sprint to the oldest of the last 3 closed sprints:

- **Up**: Recent > Oldest × 1.1 (10% improvement)
- **Down**: Recent < Oldest × 0.9 (10% decline)
- **Stable**: Within 10% variation

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (no board, no sprint, API error) |

## Common Errors

| Error | Cause |
|-------|-------|
| "No board found" | Project doesn't have an agile board |
| "No active sprint" | No sprint currently active |
| "Sprint not found" | Invalid sprint ID |
| "Access denied" | No permission to view board/sprint |

## Story Points Field

The script uses `customfield_10016` for story points (Jira default). If your instance uses a different field:

1. Find your story points field ID in Jira Admin > Issues > Custom Fields
2. Update the `fields` parameter in `get_sprint_issues()` function

## Performance Notes

- Issue fetch is limited to 200 issues per sprint
- Velocity calculation fetches up to 5 closed sprints
- For large sprints, consider using `--format json` for efficiency
