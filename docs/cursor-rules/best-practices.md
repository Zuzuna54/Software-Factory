# Cursor Rules Best Practices

## Overview

This document presents industry best practices for designing, implementing, and maintaining Cursor rules in an enterprise-grade AI development environment. These guidelines ensure rules are effective, maintainable, and optimized for performance.

## Rule Design Principles

### 1. Single Responsibility

Each rule should focus on a single aspect of guidance rather than trying to cover multiple unrelated concerns. This improves clarity and makes rules easier to manage.

**Good Example:**

```
---
description: Frontend component styling standards
globs: ["**/components/**/*.{tsx,jsx}"]
---
```

**Avoid:**

```
---
description: Frontend standards covering components, API calls, state management, and routing
globs: ["**/*.{tsx,jsx}"]
---
```

### 2. Clarity Over Brevity

Rules should be explicit and detailed rather than concise but ambiguous. Include enough information for the AI to apply the rule correctly without requiring additional context.

**Good Example:**

```
**Objective**
Ensure all database queries use parameterized statements to prevent SQL injection attacks.

**Mandatory patterns**

1. All user input must be passed as parameters using question marks or named parameters (`?` or `:name`).
2. Never concatenate strings to build SQL queries with user input.
3. Use the database driver's parameter binding mechanism (e.g., `execute(query, [params])`)
```

**Avoid:**

```
**Objective**
Use safe SQL practices.

**Mandatory patterns**

1. Don't allow SQL injection.
2. Be careful with user input.
```

### 3. Concrete Examples

Include practical examples that demonstrate the application of the rule. These serve as clear reference points for the AI when generating code.

**Good Example:**

```
**Examples**

// GOOD: Parameterized query
const query = "SELECT * FROM users WHERE id = ?";
db.execute(query, [userId]);

// BAD: String concatenation
const query = "SELECT * FROM users WHERE id = " + userId;  // Vulnerable to SQL injection
db.execute(query);
```

### 4. Appropriate Scope

Configure rules with the right scope to ensure they apply when needed without adding unnecessary context.

- **Core principles:** Use `alwaysApply: true` (project fundamentals)
- **Domain-specific guidance:** Use `globs: ["pattern"]` (language/framework specific)
- **Optional guidelines:** Use agent-requested (useful but not mandatory)
- **Reference materials:** Use manual reference (templates, examples)

## Organization Best Practices

### 1. Hierarchical Structure

Organize rules in a hierarchy from general to specific:

```
.cursor/
  rules/
    core/              # Project-wide principles
    domain/            # Domain-specific patterns
      frontend/
      backend/
      database/
    workflow/          # Process-oriented guidance
    reference/         # Templates and examples
```

### 2. Consistent Naming

Use a consistent naming convention for rule files:

```
[scope]-[concern].mdc
```

Examples:

- `core-architecture.mdc`
- `frontend-accessibility.mdc`
- `backend-security.mdc`
- `db-migrations.mdc`

### 3. Cross-Referencing

Create connections between related rules using references:

```
See also: @frontend-state-management for related patterns.
```

## Content Best Practices

### 1. Standardized Structure

Follow a consistent structure for all rules:

1. **Metadata** (description, version, scope)
2. **Objective** (clear purpose statement)
3. **Context** (when/where the rule applies)
4. **Mandatory Patterns** (specific, actionable guidance)
5. **Examples** (good and bad implementations)
6. **Verification** (how to check compliance)
7. **References** (related rules, external sources)

### 2. Actionable Guidance

Make guidance specific and actionable rather than vague:

**Good:**

````
Use the dedicated error boundary component to catch rendering errors:

```jsx
<ErrorBoundary fallback={<ErrorFallback />}>
  <ComponentThatMightError />
</ErrorBoundary>
````

```

**Avoid:**
```

Handle errors properly in components.

```

### 3. Explain Reasoning

Include rationales for guidelines to help the AI understand why they matter:

```

**Rationale:** Parameterized queries ensure proper escaping of user input, preventing SQL injection attacks that could lead to data breaches or corruption.

```

## Performance Optimization

### 1. Minimize Context Size

Keep rules concise to reduce context size:

- Aim for < 200 lines per rule file
- Split large rules into multiple focused rules
- Reference external files for lengthy examples

### 2. Progressive Disclosure

Structure rules to present the most critical information first:

```

**Objective**  
[Most important concept here]

**Key patterns**

1. [Most crucial guideline]
2. [Second most important]
   ...

**Additional details**
[Less critical information]

```

### 3. Efficient Triggering

Configure rule triggers efficiently:

- Use precise glob patterns for auto-attached rules
- Limit always-apply rules to those truly needed universally
- Use agent-requested for specialized knowledge

## Maintenance Best Practices

### 1. Version Control

Maintain a versioning system for rules:

```

---

description: API security standards
version: 1.2.0 # Major.Minor.Patch
lastUpdated: "2025-04-15"

---

```

### 2. Change Documentation

Document changes at the end of each rule:

```

---

## Changelog

- v1.2.0 (2025-04-15): Added JWT validation requirements
- v1.1.0 (2025-03-01): Added rate limiting guidelines
- v1.0.0 (2025-01-15): Initial version

---

```

### 3. Regular Review Cycle

Establish a regular review process:

- Quarterly review of all rules
- Update rules when project dependencies change
- Remove or archive obsolete rules
- Test rules with AI to ensure they're applied correctly

## Integration with Development Workflow

### 1. CI/CD Integration

Verify rule compliance in continuous integration:

- Add rule validation to PR checks
- Automate testing of rule coverage
- Track rule versioning in release notes

### 2. Onboarding

Include rule documentation in developer onboarding:

- Highlight most important rules for new team members
- Explain how to propose rule changes
- Demonstrate AI usage with project rules

### 3. Continuous Improvement

Establish a process for rule enhancement:

- Allow team members to propose rule improvements
- Collect feedback on rule effectiveness
- Track which rules are most frequently referenced
- Identify areas where additional guidance is needed
```
