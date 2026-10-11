"""Compatibility wrapper for the Ollama provider adapter."""

from kurocode.core.llm import ask_llm


def call_ollama(prompt: str, **kwargs):
    return ask_llm(prompt, provider="ollama", **kwargs)


__all__ = ["call_ollama", "ask_llm"]
