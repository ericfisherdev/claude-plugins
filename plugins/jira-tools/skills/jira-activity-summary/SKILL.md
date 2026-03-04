---
name: jira-activity-summary
description: >-
  This skill MUST be used when the user asks to summarize their own Jira
  activity, what they personally worked on, or what they did in Jira over a
  time period. Trigger phrases include "summarize my jira activity", "what did
  I do in jira", "show my jira activity", "my activity in mbc", "what did I
  work on", "jira activity report", or any request combining a personal
  possessive ("my") with a Jira project and a time period (today, yesterday,
  this week, last week, this month). This skill is specifically for personal
  activity summaries — NOT sprint reports, NOT backlog listings, NOT issue
  searches. Examples: "summarize my jira activity in mbc yesterday",
  "what did I work on in mbc this week", "show my mbc activity last week".
---

# Jira Activity Summary

Generates a structured activity report showing status changes on your assigned tickets and comment activity during a given time period.

## How to use

1. Extract the **project key** (e.g., `MBC`) and **time period** from the user's request.
2. Map the time period to one of the script's accepted values:
   - "today" → `today`
   - "yesterday" → `yesterday`
   - "this week" → `this_week`
   - "last week" → `last_week`
   - "this month" → `this_month`
3. If the project key is missing, ask the user for it before proceeding.
4. Run the script and display the output directly — no reformatting needed.

## Running the script

```bash
python <skill-dir>/scripts/jira_activity.py --project <PROJECT_KEY> --period <period>
```

Examples:
```bash
python scripts/jira_activity.py --project MBC --period yesterday
python scripts/jira_activity.py --project MBC --period this_week
python scripts/jira_activity.py --project MBC --period last_week --max-issues 200
```

`--max-issues` defaults to 100. Increase it if the user reports missing activity on busy weeks/months.

## What the report covers

**Ticket changes** — status transitions on tickets assigned to you during the period.
If a ticket moved through multiple states, the full chain is shown (e.g., `moved from To Do to In Progress to Done`).

**Comments** — three types, deduped so no comment appears twice:
- Comments you left on any ticket in the project
- Comments by others on tickets assigned to you
- Comments that @mention you (by accountId in Atlassian Document Format)

## Environment variables required

```
JIRA_BASE_URL    https://yoursite.atlassian.net
JIRA_EMAIL       your-email@example.com
JIRA_API_TOKEN   your-api-token
```

These should already be configured if the user has other jira-tools skills working.

## Output format

The script prints markdown matching this template:

```
# Jira Activity for 03/03/2026

## Ticket changes
MBC-1234 moved from To Do to In Progress
MBC-1235 moved from To Do to In Progress to Done

## Comments
### Left a comment on MBC-2345 (assigned to John Doe):
- "comment text here"

### John Doe commented on your ticket MBC-1235:
- "This looks good"

### Jane Smith mentioned you in a comment on MBC-2567:
- "comment text here"
```
