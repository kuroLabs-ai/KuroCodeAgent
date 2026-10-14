# KURO 2.0 API & Programming Interface Reference

> **Package:** `kurocode`  
> **Entry Point:** `src/kurocode`

---

## 1. Core Agent API

### `kurocode.core.agent.KuroAgent`
The primary autonomous agent class.

```python
from kurocode.core.agent import KuroAgent

agent = KuroAgent()

# Run an autonomous task (synchronously executes the ReAct loop)
# interactive=False disables interactive user prompts (raises safety error if unconfirmed)
response = agent.run("Inspect the codebase and list all routes", interactive=True)
print(response)
```

#### Key Methods:
* `run(user_input: str, interactive: bool = True) -> str`: Executes the autonomous loop up to `MAX_AUTONOMOUS_STEPS` (default: 10).
* `execute_tool(tool_data: dict, interactive: bool = True) -> dict`: Dispatches a tool action with permission verification and checkpointing.
* `parse_tool_call(text: str) -> tuple[dict | None, str]`: Robustly extracts JSON action blocks from model responses.

---

## 2. LLM Dispatch & Provider Cascade

### `kurocode.core.llm.ask_llm`
Intelligent LLM dispatcher with multi-key pool rotation and zero-downtime provider fallback.

```python
from kurocode.core.llm import ask_llm

response = ask_llm(
    prompt="Explain this error",
    system_prompt="You are a senior debugging assistant.",
    provider="gemini", # Optional: gemini | groq | openrouter | openai | ollama
    model="gemini-2.0-flash", # Optional
    history=[{"role": "user", "content": "Previous message"}],
    image_info={"b64_data": "...", "mime_type": "image/png"} # Optional multimodal
)
```

---

## 3. Dynamic Tool Registry

### `kurocode.core.plugin_registry.registry`
Global tool registration and discovery engine.

```python
from kurocode.core.plugin_registry import registry
from kurocode.core.permissions import RiskLevel

# Register a custom Python function as an agent capability
registry.register_function(
    name="calculate_vat",
    description="Calculates VAT for a given amount and rate.",
    func=lambda amount, rate=0.20: {"success": True, "total": float(amount) * (1.0 + float(rate))},
    risk_level=RiskLevel.SAFE
)
```

---

## 4. Encrypted Credential Vault

### `kurocode.core.vault.vault`
Windows DPAPI and PBKDF2 encrypted credential vault.

```python
from kurocode.core.vault import vault

# Securely set credential
vault.set_secret("MY_SERVICE_TOKEN", "secret_token_123", description="Custom API Token")

# Retrieve credential (in-memory unencrypted)
token = vault.get_secret("MY_SERVICE_TOKEN")

# Mask for logging (e.g., 'secr...123')
from kurocode.core.vault import mask_secret
print(mask_secret(token))
```

---

## 5. Self-Healing Subsystem

### `kurocode.healing.healing_engine`
Automated failure classification, root-cause diagnosis, and repair coordinator.

```python
from kurocode.healing import healing_engine

# Automatically diagnose and repair a failure
result = healing_engine.auto_heal(
    tool_name="execute_python",
    error_text_or_output="ModuleNotFoundError: No module named 'pydantic'"
)

if result.get("healed"):
    print(f"Repaired successfully via: {result.get('repair_action')}")
```

---

## 6. KuroHub & Capability Manager

### `kurocode.store.store_manager`
Unified manager for Tools, Plugins, Skills, and Integrations connected to the community hub ([`kuroLabs-ai/hub`](https://github.com/kuroLabs-ai/hub)).

```python
from kurocode.store import store_manager

# Synchronize local capabilities with online GitHub Hub (kuroLabs-ai/hub)
sync_result = store_manager.update_from_remote()
print(f"KuroHub synced: {sync_result.get('success')}")

# Search KuroHub (local built-ins + community synced)
items = store_manager.search("json")

# List capabilities by type
tool_items = store_manager.list_kurohub("tool")

# Install a capability on-demand
install_result = store_manager.install("json_inspector")

# Check installation status
installed = store_manager.is_installed(items[0])

# Publish a custom capability locally or for PR submission
store_manager.publish(
    name="my_utility",
    item_type="tool",
    description="Custom utility tool",
    payload={"code": "def run(): return {'success': True}", "entrypoint": "run"}
)
```

---

## 7. Brain Capability JSON Registries

### `kurocode.brain.kuro_hub`
Provides fast programmatic inspection of installed capabilities stored in `src/kurocode/brain/*.json`.

```python
from kurocode.brain.kuro_hub import (
    get_tools_kurohub,
    get_plugins_kurohub,
    get_skills_kurohub,
    get_integrations_kurohub,
)

# Inspect active capability registries
tools = get_tools_kurohub()             # from brain/tools.json
plugins = get_plugins_kurohub()         # from brain/plugins.json
skills = get_skills_kurohub()           # from brain/skills.json
integrations = get_integrations_kurohub() # from brain/integrations.json
```

