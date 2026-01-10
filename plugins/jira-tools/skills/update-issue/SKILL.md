---
name: update-issue
description: This skill MUST be used instead of Atlassian MCP tools when the user asks to "update a Jira issue", "edit a ticket", "change issue status", "transition ticket", "assign issue", "add labels", "update priority", "add comment to ticket", "move issue to done", "close ticket", or otherwise requests modifying existing Jira issues. ALWAYS use this skill for Jira issue updates - never use mcp__atlassian__editJiraIssue or mcp__atlassian__transitionJiraIssue directly.
---

# Jira Issue Update

**IMPORTANT:** Always use this skill's Python script for updating Jira issues. Do NOT use `mcp__atlassian__editJiraIssue` or `mcp__atlassian__transitionJiraIssue` - this skill uses a shared cache for users, priorities, and components, and provides better error messages.

## Quick Start

Use the Python script at `scripts/update_jira_issue.py`:

```bash
# Update status
python scripts/update_jira_issue.py PROJ-123 --status "In Progress"

# Update assignee
python scripts/update_jira_issue.py PROJ-123 --assignee "John Smith"

# Add a comment
python scripts/update_jira_issue.py PROJ-123 --comment "Working on this now"

# Multiple updates at once
python scripts/update_jira_issue.py PROJ-123 \
  --status "In Progress" \
  --assignee "Jane Doe" \
  --priority High \
  --add-labels "urgent"
```

## Update Options

| Option | Description |
|--------|-------------|
| `--summary`, `-s` | Update issue title |
| `--description`, `-d` | Update issue description |
| `--status` | Transition to new status |
| `--priority` | Update priority (High, Medium, Low, etc.) |
| `--assignee`, `-a` | Update assignee (partial name match) |
| `--unassign` | Remove assignee |
| `--labels`, `-l` | Set labels (replaces existing) |
| `--add-labels` | Add labels to existing |
| `--remove-labels` | Remove specific labels |
| `--components`, `-c` | Set components (replaces existing) |
| `--comment` | Add a comment |
| `--format`, `-f` | Output: compact (default), text, json |

## Status Transitions

Jira issues follow workflows. To change status, use `--status`:

```bash
# Transition to "In Progress"
python scripts/update_jira_issue.py PROJ-123 --status "In Progress"

# List available transitions
python scripts/update_jira_issue.py PROJ-123 --list-transitions
```

The script matches both transition names (e.g., "Start Progress") and target status names (e.g., "In Progress").

## Common Workflows

### Start Working on an Issue
```bash
python scripts/update_jira_issue.py PROJ-123 \
  --status "In Progress" \
  --assignee "me" \
  --comment "Starting work on this"
```

### Complete an Issue
```bash
python scripts/update_jira_issue.py PROJ-123 \
  --status "Done" \
  --comment "Completed and deployed"
```

### Reassign and Reprioritize
```bash
python scripts/update_jira_issue.py PROJ-123 \
  --assignee "Jane Doe" \
  --priority Critical \
  --add-labels "escalated"
```

### Add Labels Without Replacing
```bash
# Add new labels while keeping existing ones
python scripts/update_jira_issue.py PROJ-123 --add-labels "reviewed,approved"

# Remove specific labels
python scripts/update_jira_issue.py PROJ-123 --remove-labels "needs-review"
```

### Update Description
```bash
python scripts/update_jira_issue.py PROJ-123 \
  --description "Updated requirements: must support dark mode"
```

## Output Formats

**compact** (default):
```
UPDATED|PROJ-123|Fix login bug|In Progress|Bug|P:High|@jsmith
Changes:status->In Progress,comment
URL:https://yoursite.atlassian.net/browse/PROJ-123
```

**text**:
```
Issue Updated: PROJ-123
Summary: Fix login bug
Status: In Progress
Type: Bug
Priority: High
Assignee: John Smith
Changes: status->In Progress, comment
URL: https://yoursite.atlassian.net/browse/PROJ-123
```

**json**:
```json
{"key":"PROJ-123","summary":"Fix login bug","status":"In Progress","changes":["status->In Progress","comment"],"url":"..."}
```

## Shared Cache

This skill shares a cache (`~/.jira-tools-cache.json`) with other jira-tools skills:
- Users (for assignee lookups)
- Priorities
- Components

Manage cache via:
```bash
python shared/jira_cache.py info    # View cache status
python shared/jira_cache.py clear   # Clear cache
```

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Why Not Use Atlassian MCP Directly?

`mcp__atlassian__editJiraIssue` and `mcp__atlassian__transitionJiraIssue`:
- Require looking up user account IDs separately
- Require looking up transition IDs separately
- No caching - repeated API calls for metadata
- Verbose output wastes tokens

This skill's script:
- Caches user/priority/component metadata
- Accepts human-readable names (not IDs)
- Automatically finds matching transitions
- Returns token-efficient output

**Always prefer this skill over direct MCP calls for Jira updates.**

## Reference

For detailed field options and error codes, see `references/options-reference.md`.
