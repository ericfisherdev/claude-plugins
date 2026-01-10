---
name: issue-analysis
description: This skill MUST be used when the user asks to "analyze issue", "plan implementation", "how to fix issue", "create plan for ticket", "what's needed for this issue", "implementation strategy", "analyze Jira ticket", "plan for PROJ-123", or wants to understand how to implement a Jira issue in their codebase. Use this skill to create actionable implementation plans.
---

# Jira Issue Analysis & Implementation Planning

Analyze a Jira issue in the context of the current codebase and produce a concise implementation plan with pseudo-code.

## Workflow

When this skill is invoked, follow these steps:

### Step 1: Retrieve Issue Information

First, get the issue details. Use the cached issue if available, otherwise fetch it:

```bash
# Check cache first (from backlog-summary)
# If not cached, fetch the issue with full details
python plugins/jira-tools/skills/jira-issue/scripts/fetch_jira_issue.py ISSUE-KEY --preset full
```

Extract from the issue:
- **Summary**: What needs to be done
- **Description**: Detailed requirements, acceptance criteria
- **Labels**: Technology hints (e.g., `vue`, `api`, `backend`)
- **Comments**: Additional context, clarifications, prior discussion

### Step 2: Analyze the Codebase

Based on the issue details, explore the codebase to understand:

1. **Relevant Files**: Search for files related to the feature/bug
   - Use labels as hints (e.g., `vue` label → search `*.vue` files)
   - Search for keywords from the issue summary/description
   - Look for existing related functionality

2. **Existing Patterns**: Understand how similar features are implemented
   - Find analogous code to use as reference
   - Identify the architectural patterns in use
   - Note any relevant abstractions or utilities

3. **Dependencies**: Identify what the implementation will depend on
   - Existing services, components, or modules
   - External APIs or libraries
   - Database schemas or models

4. **Test Coverage**: Check for existing tests
   - Find test files for related functionality
   - Understand the testing patterns used

### Step 3: Check for Existing Fix

Before creating a plan, verify the issue hasn't already been addressed:

1. Search for recent commits mentioning the issue key
2. Look for code that already implements the described functionality
3. Check if the behavior described in the issue already exists

If the issue appears to be already fixed:
- Report the finding with evidence (file paths, code snippets)
- Indicate that additional work is unnecessary
- Suggest verifying with tests or manual testing

### Step 4: Create Implementation Plan

If work is needed, produce a **concise implementation plan**:

#### Plan Format

```
## Implementation Plan: ISSUE-KEY

### Summary
[One-sentence description of what will be implemented]

### Pre-conditions
- [Any setup, dependencies, or prerequisites]

### Implementation Steps

#### 1. [First major step]
**Files:** `path/to/file.ext`

[Brief description]

```pseudo
// Pseudo-code showing the approach
function/method signature
  key logic steps
  return value
```

#### 2. [Second major step]
...

### Testing Strategy
- [How to verify the implementation]

### Estimated Scope
- Files to modify: X
- New files: Y
- Complexity: Low/Medium/High
```

### Guidelines for Plans

1. **Be Concise**: Focus on the essential steps, not every detail
2. **Use Pseudo-code**: Show logic structure, not exact syntax
3. **Reference Existing Code**: Point to similar implementations as patterns
4. **Highlight Decisions**: Note any architectural choices that need confirmation
5. **Consider Edge Cases**: Mention important edge cases to handle
6. **Keep it Actionable**: Each step should be implementable

### Pseudo-code Style

Use simple, language-agnostic pseudo-code:

```pseudo
// Good: Clear intent
function validateUserInput(input):
  if input.isEmpty():
    return Error("Input required")
  if not matchesPattern(input, EMAIL_REGEX):
    return Error("Invalid email format")
  return Success(input.trim())

// Avoid: Too detailed/language-specific
const validateUserInput = (input: string): Result<string, ValidationError> => {
  if (!input || input.length === 0) {
    return { success: false, error: new ValidationError("Input required") };
  }
  // ... etc
}
```

## Output Formats

### Standard Output (Default)

Markdown implementation plan as described above.

### Already Fixed Output

```
## Issue Analysis: ISSUE-KEY

### Status: LIKELY RESOLVED

### Evidence
The functionality described in this issue appears to already exist:

- **File:** `path/to/implementation.ext`
- **Implemented:** [date/commit if found]
- **Code:** [relevant snippet]

### Verification
To confirm this issue is resolved:
1. [Test step 1]
2. [Test step 2]

### Recommendation
Close the issue after verification, or update if requirements have changed.
```

## Example Usage

User: "Analyze EFT-456 and create an implementation plan"

Claude should:
1. Fetch EFT-456 details
2. Search codebase for relevant files
3. Check if already implemented
4. Produce implementation plan or "already fixed" report

## Tips for Effective Analysis

1. **Use issue labels** to narrow down technology/area
2. **Search for domain terms** from the issue description
3. **Find similar features** to understand patterns
4. **Check recent changes** in related files
5. **Consider the full scope** - API, UI, tests, migrations

## Reference

See `references/analysis-workflow.md` for detailed exploration strategies.
