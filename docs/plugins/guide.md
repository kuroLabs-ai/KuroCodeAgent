# Plugin Guide

Plugins must provide:

- `plugin.json` manifest
- `plugin.py` entrypoint
- optional registration function named `register(registry)`

The plugin loader validates the package and registers tools into the shared runtime registry.
