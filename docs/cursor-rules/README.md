# Cursor Rules System

## Overview

This document provides a comprehensive guide to the Cursor rules system implemented in the Software Factory project. The rules system is designed to standardize AI interactions, enforce coding standards, and ensure consistent behavior across the entire autonomous multi-agent development environment.

## Purpose

Cursor rules serve as persistent, reusable context that guide AI behavior throughout the project lifecycle. They help maintain consistency, enforce standards, and encode domain-specific knowledge that would otherwise need to be repeatedly communicated to the AI.

## Rules Structure

The Cursor rules in this project follow a modular, hierarchical design with clear separation of concerns:

1. **Core Project Rules** - Define the project fundamentals and always-applicable standards
2. **Domain-Specific Rules** - Specialized guidance for specific areas (frontend, backend, testing, etc.)
3. **Workflow Rules** - Control processes and methodologies for development tasks

## Rules Architecture

All rules are stored in the `.cursor/rules` directory and are implemented using MDC format (`.mdc` files), which supports metadata and content in a single file. The rules system uses various rule types:

- **Always Apply** - Core rules always included in the model context
- **Auto-Attached** - Domain-specific rules included based on file patterns
- **Agent-Requested** - Available to the AI when relevant, based on descriptions
- **Manual** - Only included when explicitly referenced using @ruleName

## Implementation Details

For technical details about each rule and implementation guidance, see:

- [Rules Audit Report](audit-report.md) - Analysis of the current ruleset
- [Rules Implementation Guide](implementation-guide.md) - How to work with and extend rules
- [Rules Best Practices](best-practices.md) - Standards for rule creation and maintenance
