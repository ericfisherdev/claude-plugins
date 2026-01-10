# Create Issue Options Reference

## Issue Types

Common Jira issue types (varies by project configuration):
- **Bug** - Defects or problems
- **Story** - User stories for features
- **Task** - Work items
- **Epic** - Large bodies of work
- **Subtask** - Child tasks (requires --parent)

Use `--list-types` to see available types for your project.

## Priorities

Common priorities (varies by Jira configuration):
- Highest
- High
- Medium
- Low
- Lowest

## Assignee Matching

The `--assignee` flag uses partial matching on display names:
- `--assignee "John"` matches "John Smith", "John Doe"
- `--assignee "jsmith"` matches "John Smith" if display name contains it
- Case-insensitive matching

## Labels

Labels are free-form strings. Use comma-separated values:
```
--labels "bug,critical,needs-triage"
```

Labels are created automatically if they don't exist.

## Components

Components must exist in the project. Use comma-separated values:
```
--components "Frontend,API"
```

## Subtasks

To create a subtask, specify both:
- `--type Subtask` (or your project's subtask type name)
- `--parent PROJ-123` (the parent issue key)

## Description Formatting

The description is converted to Atlassian Document Format (ADF) automatically.
Plain text is supported. For complex formatting, create the issue first
then edit via the Jira UI.

## Cache File Structure

The shared cache (`~/.jira-tools-cache.json`) stores:

```json
{
  "_meta": {
    "created": "2024-01-01T00:00:00",
    "updated": "2024-01-01T12:00:00"
  },
  "projects": {
    "_cached_at": "2024-01-01T12:00:00",
    "data": [
      {"id": "10000", "key": "PROJ", "name": "Project Name"}
    ]
  },
  "issue_types_PROJ": {
    "_cached_at": "2024-01-01T12:00:00",
    "data": [
      {"id": "10001", "name": "Bug", "subtask": false}
    ]
  },
  "users_PROJ": {
    "_cached_at": "2024-01-01T12:00:00",
    "data": [
      {"accountId": "abc123", "displayName": "John Smith", "emailAddress": "john@example.com"}
    ]
  }
}
```

## Error Codes

Common API errors:
- **400**: Bad request - check field values
- **401**: Authentication failed - check credentials
- **403**: Permission denied - user lacks create permission
- **404**: Project not found - check project key

## API Endpoints Used

- `POST /rest/api/3/issue` - Create issue
- `GET /rest/api/3/project/search` - List projects
- `GET /rest/api/3/issue/createmeta/{project}/issuetypes` - List issue types
- `GET /rest/api/3/user/assignable/search` - List assignable users
- `GET /rest/api/3/project/{project}/components` - List components
- `GET /rest/api/3/priority` - List priorities
