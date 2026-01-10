---
name: create-issue
description: This skill MUST be used instead of Atlassian MCP tools when the user asks to "create a Jira issue", "create a ticket", "add a Jira ticket", "make a new issue", "file a bug", "create a story", "add a task in Jira", or otherwise requests creating new Jira issues. ALWAYS use this skill for Jira issue creation - never use mcp__atlassian__createJiraIssue directly.
---

# Jira Issue Creation

**IMPORTANT:** Always use this skill's Python script for creating Jira issues. Do NOT use `mcp__atlassian__createJiraIssue` - this skill uses a shared cache for project metadata, issue types, and users, reducing API calls and providing better error messages.

## Quick Start

Use the Python script at `scripts/create_jira_issue.py`:

```bash
# Basic issue creation
python scripts/create_jira_issue.py \
  --project PROJ \
  --type Bug \
  --summary "Login button not responding"

# Full issue with all fields
python scripts/create_jira_issue.py \
  --project PROJ \
  --type Story \
  --summary "Add dark mode support" \
  --description "Users want a dark mode toggle in settings" \
  --priority High \
  --assignee "John Smith" \
  --labels "ui,feature-request" \
  --components "Frontend"
```

## Required Arguments

| Argument | Description |
|----------|-------------|
| `--project`, `-p` | Project key (e.g., PROJ, DEV) |
| `--type`, `-t` | Issue type name (Bug, Story, Task, etc.) |
| `--summary`, `-s` | Issue title/summary |

## Optional Arguments

| Argument | Description |
|----------|-------------|
| `--description`, `-d` | Issue description text |
| `--priority` | Priority name (High, Medium, Low, etc.) |
| `--assignee`, `-a` | Assignee display name (partial match) |
| `--labels`, `-l` | Comma-separated labels |
| `--components`, `-c` | Comma-separated component names |
| `--parent` | Parent issue key (for subtasks) |
| `--format`, `-f` | Output: compact (default), text, json |

## Discovery Commands

Before creating issues, discover available options:

```bash
# List issue types for a project
python scripts/create_jira_issue.py --project PROJ --list-types

# List assignable users for a project
python scripts/create_jira_issue.py --project PROJ --list-users
```

## Shared Cache

This skill uses a shared cache (`~/.jira-tools-cache.json`) that stores:
- Project IDs and keys
- Issue types per project
- Priorities
- Assignable users per project
- Components per project
- Labels

Cache reduces API calls and enables quick lookups. Data auto-expires:
- Projects, issue types, statuses, priorities: 24 hours
- Users: 4 hours
- Components, labels: 12 hours

### Cache Management

```bash
# View cache info
python shared/jira_cache.py info

# Clear cache
python shared/jira_cache.py clear

# Force refresh cache
python shared/jira_cache.py refresh --project PROJ
```

## Output Formats

**compact** (default):
```
CREATED|PROJ-123|Login button not responding|Open|Bug|P:High|@jsmith
URL:https://yoursite.atlassian.net/browse/PROJ-123
```

**text**:
```
Issue Created: PROJ-123
Summary: Login button not responding
Status: Open
Type: Bug
Priority: High
Assignee: John Smith
URL: https://yoursite.atlassian.net/browse/PROJ-123
```

**json**:
```json
{"key":"PROJ-123","summary":"Login button not responding","status":"Open","type":"Bug","url":"..."}
```

## Common Workflows

### Create a Bug
```bash
python scripts/create_jira_issue.py \
  -p PROJ -t Bug \
  -s "Error on checkout page" \
  -d "Users see 500 error when clicking checkout" \
  --priority High
```

### Create a Story with Assignee
```bash
python scripts/create_jira_issue.py \
  -p PROJ -t Story \
  -s "User profile page redesign" \
  -a "Jane Doe" \
  -l "design,frontend"
```

### Create a Subtask
```bash
python scripts/create_jira_issue.py \
  -p PROJ -t Subtask \
  -s "Write unit tests" \
  --parent PROJ-100
```

## Error Handling

The script provides clear errors for common issues:
- Invalid project key
- Unknown issue type (with hint to use --list-types)
- User not found (with hint to use --list-users)
- Missing required fields
- Permission denied

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Why Not Use Atlassian MCP Directly?

`mcp__atlassian__createJiraIssue` requires:
- Looking up project IDs separately
- Looking up issue type IDs separately
- Looking up user account IDs separately
- No caching - repeated API calls

This skill's script:
- Caches all metadata locally
- Accepts human-readable names (not IDs)
- Provides discovery commands
- Returns token-efficient output
