"""Compatibility wrapper for the OpenRouter provider adapter."""

from kurocode.core.llm import ask_llm


def call_openrouter(prompt: str, **kwargs):
    return ask_llm(prompt, provider="openrouter", **kwargs)


__all__ = ["call_openrouter"]
