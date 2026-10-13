"""Compatibility wrapper for the Mistral AI provider adapter."""

from kurocode.core.llm import ask_llm


def call_mistral(prompt: str, **kwargs):
    return ask_llm(prompt, provider="mistral", **kwargs)


__all__ = ["call_mistral"]
