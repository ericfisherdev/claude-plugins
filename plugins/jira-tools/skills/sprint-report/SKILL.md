---
name: sprint-report
description: This skill MUST be used when the user asks for "sprint report", "sprint summary", "sprint burndown", "sprint velocity", "sprint metrics", "how is the sprint going", "sprint health", "sprint completion", or needs a detailed analysis of sprint progress and performance.
---

# Sprint Report

Generate detailed sprint reports with progress metrics, issue breakdown, and velocity data.

## Quick Start

Use the Python script at `scripts/sprint_report.py`:

```bash
# Report for active sprint
python scripts/sprint_report.py PROJ

# Report for specific sprint
python scripts/sprint_report.py PROJ --sprint-id 123

# Include detailed issue breakdown
python scripts/sprint_report.py PROJ --detailed

# Compare with previous sprints (velocity)
python scripts/sprint_report.py PROJ --velocity
```

## Options

| Option | Description |
|--------|-------------|
| `PROJECT` | Project key (required) |
| `--sprint-id ID` | Report for specific sprint (default: active) |
| `--detailed` | Include issue-by-issue breakdown |
| `--velocity` | Include velocity comparison with past sprints |
| `--format FORMAT` | Output: compact (default), text, json |

## Report Sections

### Progress Summary
- Issues: done / in-progress / todo
- Story points: completed / remaining
- Percentage complete

### Issue Breakdown (with --detailed)
- Issues by status
- Issues by type (Bug, Story, Task, etc.)
- Top blockers/risks

### Velocity (with --velocity)
- Current sprint vs average
- Last 3 sprints comparison
- Trend indicator

## Output Examples

### Compact (default)
```
SPRINT|Sprint 23|active|2024-01-15|2024-01-29|60%
ISSUES|12/20 done|5 in-progress|3 todo
POINTS|21/34|13 remaining
```

### With Velocity
```
SPRINT|Sprint 23|active|2024-01-15|2024-01-29|60%
ISSUES|12/20 done|5 in-progress|3 todo
POINTS|21/34|13 remaining
VELOCITY|34|avg:32|trend:up
```

### Text Format
```
Sprint Report: Sprint 23
========================
Status: active
Period: 2024-01-15 to 2024-01-29

Progress
--------
Issues: 12/20 done (60%)
  - In Progress: 5
  - To Do: 3

Story Points: 21/34 completed
  - Remaining: 13 points

Velocity
--------
Current Sprint: 34 points planned
Average (3 sprints): 32 points
Trend: Improving
```

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Reference

For complete options and metrics explanation, see `references/options-reference.md`.
