import os
from typing import Dict, List, Optional, Tuple
import requests

from kurocode.core import config
from kurocode.brain.models import get_provider_spec


def ask_llm(
    prompt: str,
    system_prompt: str = None,
    provider: str = None,
    model: str = None,
    history: list = None,
    image_info: dict = None
) -> str:
    """
    Intelligent LLM Dispatcher with Multi-Key Pool Rotation & Provider Cascade.
    Supports multimodal Vision requests via image_info.
    """
    sys_prompt = system_prompt or "You are KURO, a CLI-based AI system assistant running locally. Be concise, accurate, and execution-focused."

    # Try requested provider first, then cascade to remaining available providers
    if provider:
        providers_to_try = [provider] + [p for p in config.PROVIDER_CHAIN if p.lower() != provider.lower()]
    else:
        providers_to_try = config.PROVIDER_CHAIN

    last_error = ""

    for prov in providers_to_try:
        prov = prov.lower()
        pool = config.KEY_POOLS.get(prov)
        if not pool and prov != "ollama":
            continue

        # Get list of models to try for this provider
        if model and prov == provider:
            models_for_prov = [model] + [m for m in config.MODEL_CHAINS.get(prov, []) if m != model]
        else:
            models_for_prov = config.MODEL_CHAINS.get(prov, [])

        if not models_for_prov:
            models_for_prov = [config.get_active_model(prov)]

        # Try available keys for this provider
        max_key_attempts = max(1, len(pool.keys) if pool else 1)
        for _ in range(max_key_attempts):
            api_key = pool.get_available_key() if pool else "none"
            if not api_key and prov != "ollama":
                break

            for target_model in models_for_prov:
                success, response, status_code = _dispatch_request(
                    provider=prov,
                    model=target_model,
                    api_key=api_key,
                    prompt=prompt,
                    system_prompt=sys_prompt,
                    history=history,
                    image_info=image_info
                )

                if success:
                    return response

                last_error = response

                # Handle Rate Limit / Quota Exhaustion (429)
                if status_code == 429:
                    if pool and api_key:
                        pool.mark_rate_limited(api_key, cooldown_seconds=60.0)
                    continue

                # Handle Temporary Server Unavailable (503, 502, 504, 500) -> Try next model immediately
                elif status_code in (500, 502, 503, 504):
                    continue

                # Handle Invalid / Expired Key (401, 403)
                elif status_code in (401, 403):
                    if pool and api_key:
                        pool.mark_invalid(api_key)
                    break

                # Handle Model Not Found (404) -> Continue to next model
                elif status_code == 404:
                    continue

    if not last_error:
        return ("[KURO Setup Notice]\n"
                "No active API keys found or all configured keys are cooling down.\n\n"
                "Use `/key <YOUR_API_KEY>` or `/key <provider> <YOUR_API_KEY>` inside KURO to add a key,\n"
                "or set GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY in your .env file.\n"
                "Free Gemini Key: https://aistudio.google.com/app/apikey\n"
                "Free Groq Key: https://console.groq.com/keys")

    return last_error


def _normalize_messages(system_prompt: str, prompt: str, history: Optional[list] = None) -> List[Dict[str, str]]:
    """Helper to convert conversation history into standard chat messages."""
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for item in history:
            raw_role = item.get("role", "user")
            norm_role = "assistant" if raw_role in ("model", "assistant", "ai") else ("system" if raw_role == "system" else "user")
            messages.append({"role": norm_role, "content": item.get("content", "")})
    messages.append({"role": "user", "content": prompt})
    return messages


def _dispatch_request(
    provider: str,
    model: str,
    api_key: str,
    prompt: str,
    system_prompt: str,
    history: list = None,
    image_info: dict = None
) -> Tuple[bool, str, int]:
    """
    Dispatches request dynamically using metadata from models.json registry
    or specialized protocol handlers.
    """
    prov_lower = provider.lower()

    if prov_lower == "gemini":
        return _call_gemini_api(prompt, system_prompt, model, api_key, history, image_info)
    elif prov_lower == "anthropic":
        return _call_anthropic_api(prompt, system_prompt, model, api_key, history, image_info)
    elif prov_lower == "cloudflare":
        return _call_cloudflare_api(prompt, system_prompt, model, api_key, history)
    elif prov_lower == "ollama":
        url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/chat/completions"
        return _call_openai_compatible(url=url, api_key="ollama", model=model, prompt=prompt, system_prompt=system_prompt, history=history)

    # All OpenAI-compatible providers: driven directly by models.json registry
    spec = get_provider_spec(prov_lower)
    if spec:
        base_url = spec.get("base_url", "")
        # Allow environment variable override for base URL (e.g. OPENROUTER_BASE_URL, OPENAI_BASE_URL)
        env_base = os.getenv(f"{prov_lower.upper()}_BASE_URL")
        endpoint_base = env_base or base_url
        url = f"{endpoint_base.rstrip('/')}/chat/completions"
        return _call_openai_compatible(
            url=url,
            api_key=api_key,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            history=history
        )

    return False, f"Unknown provider '{provider}'", 400


def _call_gemini_api(
    prompt: str,
    system_prompt: str,
    model: str,
    api_key: str,
    history: list = None,
    image_info: dict = None
) -> Tuple[bool, str, int]:
    """Direct REST call to Gemini v1beta API with Multimodal Vision support."""
    if not api_key:
        return False, "GEMINI_API_KEY is missing", 401

    spec = get_provider_spec("gemini") or {}
    base_url = spec.get("base_url", "https://generativelanguage.googleapis.com/v1beta")
    url = f"{base_url.rstrip('/')}/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    contents = []
    if history:
        for item in history:
            role = "user" if item.get("role") in ("user", "human") else "model"
            contents.append({"role": role, "parts": [{"text": item.get("content", "")}]})

    user_parts = []
    if image_info and image_info.get("b64_data"):
        user_parts.append({
            "inline_data": {
                "mime_type": image_info.get("mime_type", "image/png"),
                "data": image_info.get("b64_data")
            }
        })
    user_parts.append({"text": prompt})
    contents.append({"role": "user", "parts": user_parts})

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096
        }
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts:
                    return True, parts[0].get("text", ""), 200
            return True, "[KURO] Received empty content from Gemini.", 200
        else:
            return False, f"[Gemini {res.status_code}] {res.text}", res.status_code
    except Exception as e:
        return False, f"[Connection Error] Gemini API unreachable: {str(e)}", 503


def _call_openai_compatible(
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    system_prompt: str,
    history: list = None
) -> Tuple[bool, str, int]:
    """Generic OpenAI-compatible API caller for Groq, OpenRouter, Mistral, OpenAI, DeepSeek, xAI, Ollama."""
    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"

    messages = _normalize_messages(system_prompt, prompt, history)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            choices = data.get("choices", [])
            if choices:
                return True, choices[0].get("message", {}).get("content", ""), 200
            return True, "[KURO] Received empty response.", 200
        else:
            return False, f"[API Error {res.status_code}] {res.text}", res.status_code
    except Exception as e:
        return False, f"[Connection Error] API unreachable ({url}): {str(e)}", 503


def _call_anthropic_api(
    prompt: str,
    system_prompt: str,
    model: str,
    api_key: str,
    history: list = None,
    image_info: dict = None
) -> Tuple[bool, str, int]:
    """Native REST call to Anthropic Messages API."""
    if not api_key:
        return False, "ANTHROPIC_API_KEY is missing", 401

    spec = get_provider_spec("anthropic") or {}
    base_url = os.getenv("ANTHROPIC_BASE_URL", spec.get("base_url", "https://api.anthropic.com/v1"))
    version = spec.get("api_version", "2023-06-01")

    url = f"{base_url.rstrip('/')}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": version,
        "content-type": "application/json"
    }

    messages = []
    if history:
        for item in history:
            raw_role = item.get("role", "user")
            norm_role = "assistant" if raw_role in ("model", "assistant", "ai") else "user"
            messages.append({"role": norm_role, "content": item.get("content", "")})

    user_content = []
    if image_info and image_info.get("b64_data"):
        user_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_info.get("mime_type", "image/png"),
                "data": image_info.get("b64_data")
            }
        })
    user_content.append({"type": "text", "text": prompt})
    messages.append({"role": "user", "content": user_content if len(user_content) > 1 else prompt})

    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": messages,
        "temperature": 0.2
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            content_blocks = data.get("content", [])
            for block in content_blocks:
                if block.get("type") == "text":
                    return True, block.get("text", ""), 200
            return True, "[KURO] Received empty response from Anthropic.", 200
        else:
            return False, f"[Anthropic {res.status_code}] {res.text}", res.status_code
    except Exception as e:
        return False, f"[Connection Error] Anthropic API unreachable: {str(e)}", 503


def _call_cloudflare_api(
    prompt: str,
    system_prompt: str,
    model: str,
    api_key: str,
    history: list = None
) -> Tuple[bool, str, int]:
    """Direct REST call to Cloudflare Workers AI endpoint."""
    account_id = config.CLOUDFLARE_ACCOUNT_ID
    if not account_id:
        return False, "CLOUDFLARE_ACCOUNT_ID is required to use Cloudflare Workers AI", 400
    if not api_key:
        return False, "CLOUDFLARE_API_TOKEN is missing", 401

    spec = get_provider_spec("cloudflare") or {}
    template_url = spec.get("base_url", "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run")
    base_url = template_url.replace("{account_id}", account_id)
    url = f"{base_url.rstrip('/')}/{model}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Normalize messages using common helper
    messages = _normalize_messages(system_prompt, prompt, history)
    payload = {"messages": messages}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            result = data.get("result", {})
            response_text = result.get("response", "")
            if response_text:
                return True, response_text, 200
            return True, "[KURO] Received empty response from Cloudflare Workers AI.", 200
        else:
            return False, f"[Cloudflare {res.status_code}] {res.text}", res.status_code
    except Exception as e:
        return False, f"[Connection Error] Cloudflare API unreachable: {str(e)}", 503
