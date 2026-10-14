---
name: tdd_refactoring
version: 1.0.0
description: Test-Driven Development refactoring routine (Red -> Green -> Refactor -> Verify).
author: kuroLabs-ai
tags: [tdd, testing, refactoring]
---

# TDD Refactoring Skill Routine

This procedure defines the disciplined Test-Driven Development cycle for KuroCode.

## Steps:
1. **Red**: Identify targeted behavior and write a minimal failing unit test in `tests/`.
2. **Green**: Make the smallest verified code change necessary to turn the test green.
3. **Refactor**: Clean up the architecture, improve types, remove code smells without altering external behavior.
4. **Verify**: Run full test suite to guarantee 0 regressions, then create a Git checkpoint.
