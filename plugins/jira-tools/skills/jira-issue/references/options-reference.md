# Jira Issue Fetch Options Reference

## Presets

| Preset | Fields | Description | Comments | Est. Tokens |
|--------|--------|-------------|----------|-------------|
| `minimal` | summary, status | None | None | ~20 |
| `standard` | summary, status, type, priority, assignee, description | 500 chars | 3 @ 200 chars | ~200 |
| `full` | All core fields | 1500 chars | 10 @ 400 chars | ~500 |

## Available Fields

**Low Token Impact:**
- `summary` - Issue title
- `status` - Current status name
- `issuetype` - Bug, Story, Task, etc.
- `priority` - Priority level
- `assignee` - Assigned user display name
- `reporter` - Creator display name
- `created` - Creation date (YYYY-MM-DD)
- `updated` - Last update date (YYYY-MM-DD)

**Medium Token Impact:**
- `labels` - Array of label strings
- `components` - Array of component names

**High Token Impact:**
- `description` - Full description (use --max-desc to truncate)

## Output Formats

### compact (default, lowest tokens)
```
PROJ-123|Fix login bug|In Progress|Bug|P:High|@jsmith
Desc:Users report timeout after 30 seconds...
[Alice]First comment text...
```

### text (readable, moderate tokens)
```
Issue: PROJ-123
Summary: Fix login bug
Status: In Progress
...
```

### json (structured, moderate tokens)
```json
{"key":"PROJ-123","summary":"Fix login bug","status":"In Progress"}
```

### markdown (formatted, higher tokens)
```markdown
# PROJ-123: Fix login bug

**Status:** In Progress | **Type:** Bug
```

## Truncation Behavior

- `--max-desc 0` excludes description entirely
- Truncated text ends with `...`
- Comments ordered by most recent first
- Empty/null fields omitted from compact/json output

## Environment Variables

```bash
export JIRA_BASE_URL="https://yoursite.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="your-api-token"
```

## Error Codes

- 401: Authentication failed - check JIRA_EMAIL and JIRA_API_TOKEN
- 403: Access denied - user lacks permission for this issue
- 404: Issue not found - verify issue key exists
