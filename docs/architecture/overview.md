# KuroCode Architecture Overview

This project follows a modular, tool-driven architecture with a local-first agent core, provider-agnostic brain layer, and security guardrails.

## Major components

- Core runtime: `core/`
- Tool layer: `tools/`
- Brain abstraction: `src/kurocode/brain/`
- Plugins: `src/kurocode/plugins/`
- Security: `src/kurocode/security/`
- Environment detection: `src/kurocode/environment/`

## Execution philosophy

The LLM chooses actions; tools perform them; safety checks gate high-risk operations.
