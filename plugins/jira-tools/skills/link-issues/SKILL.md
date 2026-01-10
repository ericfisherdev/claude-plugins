---
name: link-issues
description: This skill MUST be used when the user asks to "link issues", "relate issues", "mark as duplicate", "blocks issue", "is blocked by", "create issue link", "connect issues", or otherwise requests creating relationships between Jira issues.
---

# Link Jira Issues

Create relationships between Jira issues such as "blocks", "is blocked by", "relates to", "duplicates", etc.

## Quick Start

Use the Python script at `scripts/link_issues.py`:

```bash
# Link two issues (default: "Relates")
python scripts/link_issues.py PROJ-123 PROJ-456

# Specify link type
python scripts/link_issues.py PROJ-123 PROJ-456 --type "Blocks"

# Add a comment to the outward issue
python scripts/link_issues.py PROJ-123 PROJ-456 --type "Duplicates" --comment "Found during triage"
```

## Arguments

| Argument | Description |
|----------|-------------|
| `outward_issue` | The "from" issue key (e.g., PROJ-123 blocks...) |
| `inward_issue` | The "to" issue key (e.g., ...blocks PROJ-456) |
| `--type`, `-t` | Link type name (default: "Relates") |
| `--comment`, `-c` | Optional comment on the outward issue |
| `--format`, `-f` | Output: compact (default), text, json |

## Discovery Commands

```bash
# List available link types
python scripts/link_issues.py --list-types
```

## Common Link Types

| Type | Outward | Inward |
|------|---------|--------|
| Blocks | blocks | is blocked by |
| Cloners | clones | is cloned by |
| Duplicate | duplicates | is duplicated by |
| Relates | relates to | relates to |

## Examples

### Mark as Blocking
```bash
# PROJ-100 blocks PROJ-101
python scripts/link_issues.py PROJ-100 PROJ-101 --type "Blocks"
```

### Mark as Duplicate
```bash
# PROJ-200 duplicates PROJ-150 (original)
python scripts/link_issues.py PROJ-200 PROJ-150 --type "Duplicate" --comment "Closing as duplicate"
```

### Create Relation with Comment
```bash
python scripts/link_issues.py PROJ-300 PROJ-301 --type "Relates" --comment "Related work for Q4 release"
```

## Output Formats

**compact** (default):
```
LINKED|PROJ-123->PROJ-456|Blocks
```

**text**:
```
Link Created
From: PROJ-123
To: PROJ-456
Type: Blocks (blocks -> is blocked by)
```

**json**:
```json
{"outward":"PROJ-123","inward":"PROJ-456","type":"Blocks"}
```

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Reference

For detailed link type options, see `references/options-reference.md`.
