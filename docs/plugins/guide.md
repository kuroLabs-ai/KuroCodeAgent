# KURO 2.0 Plugin & Extension Authoring Guide

> **Namespace:** `src/kurocode/plugins/`  
> **Manager:** `kurocode.plugins.manager.plugin_manager`

---

## 1. Plugin Packaging Standard

A valid KURO plugin is a directory located in `%APPDATA%\Kuro\plugins\` (or project `plugins/`) containing:

```
my_custom_plugin/
├── plugin.json       # Manifest describing metadata and permissions
├── main.py           # Entry point Python script
└── README.md         # (Optional) Documentation
```

### `plugin.json` Manifest Format:
```json
{
  "name": "my_custom_plugin",
  "version": "1.0.0",
  "description": "Custom utility capability for KURO",
  "author": "Developer Name",
  "entrypoint": "main.py",
  "category": "utilities",
  "permissions": ["read_file", "network"],
  "tools": [
    {
      "name": "custom_action",
      "description": "Performs custom calculation",
      "risk_level": "safe"
    }
  ]
}
```

### `main.py` Entry Point Format:
```python
def custom_action(data: str) -> dict:
    """Action implementation."""
    return {
        "success": True,
        "result": f"Processed: {data}"
    }

def register(registry):
    """Optional explicit registration hook into PluginRegistry."""
    from kurocode.core.permissions import RiskLevel
    registry.register_function(
        name="custom_action",
        description="Performs custom calculation",
        func=custom_action,
        risk_level=RiskLevel.SAFE
    )
```

---

## 2. Managing Plugins via CLI

* **List installed plugins**:
  ```bash
  /plugin list
  ```
* **Install plugin from local directory or Git URL**:
  ```bash
  /plugin install ./my_custom_plugin
  # or
  /plugin install https://github.com/user/kuro-plugin-sample.git
  ```
* **Remove / uninstall plugin**:
  ```bash
  /plugin remove my_custom_plugin
  ```

---

## 3. Dynamic Tool Hot-Loading via `/tool create`

KURO can author and hot-register custom Python tools at runtime without a manifest or process restart:

```bash
/tool create cube_calc def cube_calc(n: int) -> dict:\n    return {'success': True, 'result': n ** 3}
```
1. Validates code against the AST safety sandbox.
2. Compiles in an isolated module scope.
3. Automatically registers the function into `PluginRegistry`.
4. Persists the tool to `plugins/dynamic_cube_calc/tool.py`.

---

## 4. Distributing via the KuroLabs Capability Hub (`kuroLabs-ai/hub`)

To share your plugin, tool, or procedural skill with all KuroCode agents worldwide:

1. **Publish Locally**:
   ```bash
   /store publish <name> <tool|plugin|skill> <description>
   ```
2. **Submit to the Community Hub**:
   - Fork [`https://github.com/kuroLabs-ai/hub`](https://github.com/kuroLabs-ai/hub).
   - Place your tool in `tools/<name>.py`, plugin in `plugins/<name>/`, or skill in `skills/<name>/SKILL.md`.
   - Register the item in `catalog.json` with its metadata, version, tags, and entrypoint.
   - Open a pull request against `kuroLabs-ai/hub`. Once merged, every KURO agent can install it with `/store install <name>`.

