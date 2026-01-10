# Move to Sprint Options Reference

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `ISSUES` | Issue keys to move (required) | - |
| `--sprint-id ID` | Target sprint ID | Active sprint |
| `--backlog` | Move to backlog | - |
| `--next-sprint` | Move to next future sprint | - |
| `--list-sprints` | List available sprints | - |
| `--format FORMAT` | compact, text, json | compact |

## Target Selection

Only one target can be specified at a time:

| Target | Behavior |
|--------|----------|
| (none) | Move to active sprint |
| `--sprint-id ID` | Move to specific sprint |
| `--backlog` | Remove from sprint, return to backlog |
| `--next-sprint` | Move to first future sprint |

## Output Formats

### Compact (default)
```
MOVED|PROJ-123,PROJ-124|Sprint 23
```

### Text
```
Moved 2 issue(s) to Sprint 23:
  PROJ-123: Implement login
  PROJ-124: Fix validation bug
```

### JSON
```json
{
  "issues": ["PROJ-123", "PROJ-124"],
  "target": "Sprint 23",
  "summaries": {"PROJ-123": "Implement login", "PROJ-124": "Fix validation bug"}
}
```

## Sprint List Format

When using `--list-sprints`:

```
*|123|Sprint 23|active
+|124|Sprint 24|future
-|122|Sprint 22|closed
```

State icons: `*` active, `+` future, `-` closed

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (no board, invalid sprint, permission denied) |

## Common Errors

| Error | Cause |
|-------|-------|
| "No board found" | Project doesn't have an agile board |
| "No active sprint" | No sprint currently active |
| "No future sprints" | No planned sprints for --next-sprint |
| "Access denied" | Missing "Schedule Issues" permission |
| "Resource not found" | Invalid issue key or sprint ID |

## Permissions

Requires the "Schedule Issues" permission on the project's board. This permission allows:
- Moving issues to sprints
- Removing issues from sprints
- Reordering backlog

## Bulk Operations

You can move multiple issues in one command:

```bash
# Move up to 50 issues at once
python scripts/move_to_sprint.py PROJ-1 PROJ-2 PROJ-3 PROJ-4 PROJ-5

# Using shell expansion
python scripts/move_to_sprint.py PROJ-{100..110}
```

The Jira API handles multiple issues in a single request.

## API Endpoints Used

| Operation | Endpoint |
|-----------|----------|
| Move to sprint | `POST /rest/agile/1.0/sprint/{sprintId}/issue` |
| Move to backlog | `POST /rest/agile/1.0/backlog/issue` |
| List sprints | `GET /rest/agile/1.0/board/{boardId}/sprint` |
