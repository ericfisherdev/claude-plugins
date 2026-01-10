# Manage Sprint Options Reference

## Actions

| Action | Description |
|--------|-------------|
| `--create NAME` | Create a new sprint |
| `--start` | Start a sprint (future → active) |
| `--complete` | Complete a sprint (active → closed) |
| `--update` | Update sprint details |
| `--list` | List all sprints for project |

Only one action can be performed per command.

## Sprint Selection

| Option | Applies To | Description |
|--------|------------|-------------|
| `--sprint-id ID` | start, complete, update | Target specific sprint |
| `--next` | start | Use next future sprint |

### Default Behavior

| Action | Without --sprint-id |
|--------|---------------------|
| `--start` | Starts first future sprint |
| `--complete` | Completes active sprint |
| `--update` | Error (--sprint-id required) |

## Create Options

| Option | Required | Description |
|--------|----------|-------------|
| `--create NAME` | Yes | Sprint name |
| `--start-date DATE` | No | Start date (YYYY-MM-DD), default: tomorrow |
| `--end-date DATE` | No | End date (YYYY-MM-DD) |
| `--duration DAYS` | No | Duration in days (default: 14) |
| `--goal TEXT` | No | Sprint goal |

### Date Calculation

- If only `--duration` provided: starts tomorrow, ends after N days
- If only `--start-date` provided: ends after 14 days (default duration)
- If both `--start-date` and `--end-date` provided: uses exact dates

## Update Options

| Option | Description |
|--------|-------------|
| `--name NAME` | Change sprint name |
| `--start-date DATE` | Change start date |
| `--end-date DATE` | Change end date |
| `--goal TEXT` | Change sprint goal |

At least one update option is required with `--update`.

## Output Formats

### Compact (default)
```
CREATED|456|Sprint 24|future|2024-02-01|2024-02-14
STARTED|456|Sprint 24|active|2024-02-01|2024-02-14
COMPLETED|456|Sprint 24|closed|2024-02-01|2024-02-14
UPDATED|456|Sprint 24|active|2024-02-01|2024-02-21
```

### Text
```
Sprint Created
  ID: 456
  Name: Sprint 24
  State: future
  Start: 2024-02-01
  End: 2024-02-14
  Goal: Complete authentication module
```

### JSON
```json
{
  "action": "created",
  "sprint": {
    "id": 456,
    "name": "Sprint 24",
    "state": "future",
    "startDate": "2024-02-01T09:00:00.000Z",
    "endDate": "2024-02-14T17:00:00.000Z",
    "goal": "Complete authentication module"
  }
}
```

## Sprint States

| State | Description | Can Transition To |
|-------|-------------|-------------------|
| `future` | Planned sprint | active |
| `active` | Currently running | closed |
| `closed` | Completed | (none) |

### State Transition Rules

- Only one sprint can be `active` at a time
- Cannot start a sprint that's already active or closed
- Cannot complete a sprint that's not active
- Cannot reopen a closed sprint

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (no board, invalid state transition, permission denied) |

## Common Errors

| Error | Cause |
|-------|-------|
| "No board found" | Project doesn't have an agile board |
| "No future sprints to start" | No planned sprints exist |
| "No active sprint to complete" | No sprint is currently running |
| "Sprint is already active" | Cannot start an active sprint |
| "Access denied" | Missing "Manage Sprints" permission |

## Permissions

Requires "Manage Sprints" permission on the board:
- Create new sprints
- Start/complete sprints
- Update sprint details

## API Endpoints Used

| Operation | Endpoint |
|-----------|----------|
| Create sprint | `POST /rest/agile/1.0/sprint` |
| Update sprint | `POST /rest/agile/1.0/sprint/{sprintId}` |
| List sprints | `GET /rest/agile/1.0/board/{boardId}/sprint` |

Note: Starting and completing sprints use the update endpoint with `state` field.

## Examples

### Full Sprint Lifecycle
```bash
# 1. Create next sprint
python manage_sprint.py PROJ --create "Sprint 25" --goal "API refactor"

# 2. When ready, start it
python manage_sprint.py PROJ --start --next

# 3. At end of sprint, complete it
python manage_sprint.py PROJ --complete
```

### Extend a Sprint
```bash
# Add 3 more days to active sprint
python manage_sprint.py PROJ --update --sprint-id 456 --end-date 2024-02-17
```

### Quick Sprint Setup
```bash
# Create 1-week sprint starting today
python manage_sprint.py PROJ --create "Hotfix Sprint" \
  --start-date $(date +%Y-%m-%d) --duration 7
```
