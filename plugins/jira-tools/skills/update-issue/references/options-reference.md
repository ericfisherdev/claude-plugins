# Update Issue Options Reference

## Field Updates

### Summary
```bash
--summary "New issue title"
```
Updates the issue title/summary.

### Description
```bash
--description "Full description text here"
```
Replaces the entire description. Plain text is converted to Atlassian Document Format.

### Priority
```bash
--priority High
```
Common priorities (varies by Jira configuration):
- Highest
- High
- Medium
- Low
- Lowest

### Assignee
```bash
--assignee "John Smith"    # Partial match on display name
--assignee "jsmith"        # Also matches if in display name
--unassign                 # Remove assignee
```
Uses partial, case-insensitive matching on display names.

## Labels

### Replace All Labels
```bash
--labels "bug,critical,needs-review"    # Set these labels
--labels ""                              # Remove all labels
```

### Add Labels (Keep Existing)
```bash
--add-labels "reviewed,approved"
```
Adds to existing labels without removing any.

### Remove Specific Labels
```bash
--remove-labels "needs-review,draft"
```
Removes only the specified labels, keeps others.

## Components
```bash
--components "Frontend,API"    # Set these components
--components ""                 # Remove all components
```
Component names must match exactly (case-insensitive).

## Status Transitions

### Transition to Status
```bash
--status "In Progress"
--status "Done"
--status "Closed"
```

The script matches against:
1. Transition name (e.g., "Start Progress")
2. Target status name (e.g., "In Progress")

### List Available Transitions
```bash
python update_jira_issue.py PROJ-123 --list-transitions
```

Output:
```
Available transitions for PROJ-123:
  - Start Progress -> In Progress
  - Close Issue -> Closed
  - Resolve -> Done
```

### Common Workflow Transitions

| From Status | Common Transitions |
|------------|-------------------|
| Open/Backlog | Start Progress, In Progress |
| In Progress | Done, Closed, Review, Blocked |
| Review | Done, In Progress, Rejected |
| Done | Reopen, Closed |

Note: Available transitions depend on your Jira workflow configuration.

## Comments
```bash
--comment "This is my comment text"
```
Adds a new comment to the issue. Plain text only.

## Multiple Updates

Combine multiple options in one command:
```bash
python update_jira_issue.py PROJ-123 \
  --summary "Updated title" \
  --status "In Progress" \
  --assignee "Jane Doe" \
  --priority High \
  --add-labels "urgent,sprint-42" \
  --comment "Taking ownership of this issue"
```

Order of operations:
1. Field updates (summary, description, priority, assignee, labels, components)
2. Status transition
3. Comment added

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| User not found | Assignee name doesn't match | Check spelling or use `--list-users` in create-issue |
| Cannot transition | Status not reachable | Use `--list-transitions` to see available options |
| Component not found | Component doesn't exist | Check project components in Jira |
| Priority not found | Invalid priority name | Use standard names: Highest, High, Medium, Low, Lowest |

### Permission Errors
- 403: User lacks permission to edit the issue
- 404: Issue doesn't exist or user can't view it

## API Endpoints Used

- `PUT /rest/api/3/issue/{issueKey}` - Update fields
- `POST /rest/api/3/issue/{issueKey}/transitions` - Change status
- `POST /rest/api/3/issue/{issueKey}/comment` - Add comment
- `GET /rest/api/3/issue/{issueKey}/transitions` - List available transitions

## Output Changes Tracking

The `changes` field in output shows what was modified:
- `summary` - Summary was updated
- `description` - Description was updated
- `priority` - Priority was changed
- `assignee` - Assignee was changed
- `unassigned` - Assignee was removed
- `labels` - Labels were replaced
- `labels+` - Labels were added
- `labels-` - Labels were removed
- `components` - Components were changed
- `status->StatusName` - Transitioned to new status
- `comment` - Comment was added
