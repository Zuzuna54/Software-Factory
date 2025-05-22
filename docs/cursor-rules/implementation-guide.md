# Cursor Rules Implementation Guide

## Introduction

This guide provides detailed instructions for implementing, extending, and maintaining the Cursor rules system in the Software Factory project. It explains the technical details of how rules are structured, how they interact, and best practices for modifying them.

## Rule File Structure

Each rule in the Software Factory project follows a standardized MDC (Markdown with Frontmatter) format:

````
---
description: Short description of the rule's purpose
version: 1.0.0
globs: ["**/*.ts", "**/*.tsx"]  # Optional: Files to which this rule applies
alwaysApply: true|false         # Whether the rule is always applied
---

**Objective**
Clear statement of what the rule aims to achieve.

**Mandatory patterns**

1. First pattern to follow
2. Second pattern to follow
3. ...

**Verification checklist**

- [ ] First verification item
- [ ] Second verification item
- [ ] ...

**Examples**

```code-example
// Example code showing the rule in action
````

```

## Rule Types

The system supports four types of rules:

1. **Always Apply Rules** (`alwaysApply: true`) - These rules are always included in the model context and apply to all interactions. Use sparingly for fundamentals that apply project-wide.

2. **Auto-Attached Rules** (`globs: ["pattern1", "pattern2"]`) - These rules are automatically included when working with files that match the specified glob patterns. Ideal for language-specific or domain-specific rules.

3. **Agent-Requested Rules** (`description` provided, no other trigger) - These rules are available to the AI, which decides whether to include them based on relevance. They must include a clear description for the AI to understand when to apply them.

4. **Manual Rules** (No triggers defined) - These rules are only included when explicitly referenced using @ruleName notation.

## Rule Organization

The project uses a nested directory structure for rules organization:

```

.cursor/
rules/ # Core rules (always apply)
project-overview.mdc
simplicity-first.mdc
...

    # Domain-specific rules in subdirectories
    frontend/
      components.mdc
      styling.mdc
      ...

    backend/
      api.mdc
      database.mdc
      ...

    testing/
      unit-tests.mdc
      e2e-tests.mdc
      ...

```

This structure allows rules to be closer to the code they govern and makes them easier to discover and maintain.

## Implementing New Rules

To implement a new rule:

1. Identify the appropriate category for the rule (core, domain-specific, etc.)
2. Choose the correct directory for the rule based on its scope
3. Create a new `.mdc` file with a descriptive name
4. Use the standard rule template format
5. Set appropriate metadata (description, version, application scope)
6. Define clear objectives, patterns, verification items, and examples
7. Reference any external files if needed using `@filename` notation
8. Test the rule with relevant AI interactions to ensure it works as expected

## Modifying Existing Rules

When modifying existing rules:

1. Update the version number in the metadata section
2. Document changes in a comment at the end of the file
3. Ensure the rule remains compatible with other rules
4. Update any referenced files if needed
5. Verify the rule still functions as expected with test interactions

## Referenced Files

Rules can reference external files using the `@filename` notation. This is useful for:

- Including code templates
- Referencing examples of correct implementation
- Including complex patterns that are easier to understand in context

Referenced files should be:
- Small and focused (< 100 lines)
- Clearly commented
- Located near the rule that references them

## Rule Versioning

All rules include version metadata to track changes:

- Format: `version: MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: Feature additions, non-breaking changes
- PATCH: Bug fixes, clarifications

## Interactions Between Rules

Rules can reference other rules using the notation `@ruleName`. This creates a hierarchical system where:

- Core rules establish foundations
- Domain-specific rules extend core principles
- Specialized rules provide detailed guidance

When rules interact:
- More specific rules take precedence over general ones
- Domain-specific rules add to but don't override core rules
- Conflicts should be resolved by explicit precedence statements

## Testing Rules

Every rule should be tested to ensure it functions correctly:

1. Create a test interaction that targets the rule's domain
2. Verify the AI applies the patterns correctly
3. Check that verification items actually catch violations
4. Document edge cases and expected behavior

## Maintenance and Governance

Rules maintenance follows these principles:

1. **Regular Review** - Rules should be reviewed quarterly
2. **Change Control** - Major changes require team approval
3. **Documentation** - All changes must be documented
4. **Backward Compatibility** - Breaking changes should be minimized
5. **Performance** - Rules should be optimized to minimize context size
```
