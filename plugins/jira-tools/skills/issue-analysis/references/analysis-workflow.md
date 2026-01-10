# Issue Analysis Workflow Reference

Detailed strategies for analyzing Jira issues and creating implementation plans.

## Phase 1: Issue Comprehension

### Extract Key Information

From the Jira issue, identify:

| Element | Questions to Answer |
|---------|---------------------|
| **What** | What feature/fix is requested? |
| **Why** | What problem does this solve? |
| **Who** | Who is affected? (users, systems) |
| **Where** | What part of the system? |
| **Constraints** | Any specific requirements or limitations? |

### Decode Labels

Common label meanings for search guidance:

| Label | Search Strategy |
|-------|-----------------|
| `vue`, `frontend`, `ui` | `*.vue`, `*.tsx`, `components/` |
| `api`, `backend` | `controllers/`, `routes/`, `services/` |
| `database`, `db` | `migrations/`, `models/`, `*.sql` |
| `auth`, `security` | `auth/`, `middleware/`, `guards/` |
| `performance` | Look for N+1 queries, loops, caching |
| `bug`, `hotfix` | Search error messages, stack traces |

## Phase 2: Codebase Exploration

### Search Strategy

1. **Keyword Search** - Search for terms from the issue
   ```
   Grep for: feature name, domain terms, error messages
   ```

2. **File Pattern Search** - Based on labels/technology
   ```
   Glob for: *.vue, *Controller.*, *Service.*, etc.
   ```

3. **Structural Search** - Find related architecture
   ```
   Look for: similar features, shared patterns, base classes
   ```

### Exploration Checklist

- [ ] Search for issue key in comments/commit messages
- [ ] Find files with related functionality
- [ ] Identify the entry point (API route, UI component, etc.)
- [ ] Trace the data flow through the system
- [ ] Locate relevant tests
- [ ] Check for existing utilities/helpers to reuse

### Common File Locations

| Feature Type | Typical Locations |
|--------------|-------------------|
| API Endpoint | `routes/`, `controllers/`, `handlers/` |
| Business Logic | `services/`, `domain/`, `core/` |
| Data Access | `repositories/`, `models/`, `dal/` |
| UI Component | `components/`, `views/`, `pages/` |
| State Management | `store/`, `state/`, `reducers/` |
| Utilities | `utils/`, `helpers/`, `lib/` |
| Configuration | `config/`, `.env`, `settings/` |
| Tests | `tests/`, `__tests__/`, `*.test.*`, `*.spec.*` |

## Phase 3: Existing Fix Detection

### Signs of Prior Implementation

1. **Code Comments**
   ```
   // JIRA: PROJ-123 - Added validation
   // Fixes issue with user input
   ```

2. **Git History**
   ```bash
   git log --oneline --grep="PROJ-123"
   git log --oneline --all -- path/to/related/file
   ```

3. **Functional Equivalence**
   - Feature described already exists
   - Bug behavior no longer reproducible
   - Similar functionality under different name

### Verification Approach

If potential fix found:

1. **Compare Requirements**: Does existing code meet all criteria?
2. **Check Coverage**: Are edge cases handled?
3. **Test Evidence**: Do tests validate the fix?
4. **Recent Activity**: When was the file last modified?

## Phase 4: Implementation Planning

### Breaking Down Work

For each significant change:

```
1. Identify the file(s) to modify
2. Determine the function/method to add/change
3. Outline the logic flow
4. Note dependencies and imports
5. Consider error handling
6. Plan test coverage
```

### Pseudo-code Patterns

#### Adding a New Function

```pseudo
function newFeatureName(params):
  // 1. Validate input
  validate(params)

  // 2. Fetch required data
  data = repository.getData(params.id)

  // 3. Apply business logic
  result = processData(data, params.options)

  // 4. Persist changes
  repository.save(result)

  // 5. Return response
  return formatResponse(result)
```

#### Modifying Existing Logic

```pseudo
// BEFORE (existing code reference)
function existingFunction(x):
  return process(x)

// AFTER (proposed change)
function existingFunction(x):
  // NEW: Add validation
  if not isValid(x):
    throw ValidationError

  // EXISTING: Keep original logic
  return process(x)
```

#### Adding UI Component

```pseudo
Component NewFeature:
  // State
  state = { loading, data, error }

  // Lifecycle
  onMount:
    fetchData()

  // Methods
  fetchData():
    state.loading = true
    try:
      state.data = await api.getData()
    catch error:
      state.error = error.message
    finally:
      state.loading = false

  // Render
  render:
    if loading: show Spinner
    if error: show ErrorMessage
    else: show DataDisplay(data)
```

### Complexity Assessment

| Complexity | Indicators |
|------------|------------|
| **Low** | Single file, isolated change, clear pattern to follow |
| **Medium** | Multiple files, some new logic, existing tests to update |
| **High** | Cross-cutting concern, new patterns needed, significant testing |

### Risk Identification

Flag potential risks in the plan:

- **Breaking Changes**: API contracts, database schema
- **Performance**: New queries, loops, large data
- **Security**: Input validation, auth checks, data exposure
- **Dependencies**: External services, version compatibility

## Phase 5: Plan Output

### Concise Plan Template

```markdown
## Implementation Plan: ISSUE-KEY

### Summary
[One sentence: what + why]

### Approach
[Brief architectural decision if needed]

### Steps

1. **[Action]** in `path/file`
   ```pseudo
   [key logic]
   ```

2. **[Action]** in `path/file`
   ```pseudo
   [key logic]
   ```

### Tests
- [ ] Unit test for [scenario]
- [ ] Integration test for [flow]

### Notes
- [Any risks, decisions, or follow-ups]
```

### Already Fixed Template

```markdown
## Issue Analysis: ISSUE-KEY

### Status: LIKELY RESOLVED

### Finding
[What was found that addresses the issue]

**Location:** `path/to/file:line`
```pseudo
// Relevant code snippet
```

### Verification Steps
1. [How to confirm fix works]
2. [Edge cases to test]

### Recommendation
[Close/Verify/Partially addressed - needs X]
```

## Quick Reference

### Search Commands

```bash
# Find files by pattern
glob: **/*Controller*.php

# Search code content
grep: "functionName" --type php

# Search in specific directory
grep: "pattern" path/to/search/
```

### Common Issue Types

| Issue Type | Analysis Focus |
|------------|----------------|
| Bug | Error messages, stack traces, repro steps |
| Feature | Similar features, architectural patterns |
| Enhancement | Existing implementation, extension points |
| Refactor | Current structure, test coverage |
| Performance | Profiling points, query analysis |
