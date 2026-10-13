"""Compatibility wrapper for the Anthropic provider adapter."""

from kurocode.core.llm import ask_llm


def call_anthropic(prompt: str, **kwargs):
    return ask_llm(prompt, provider="anthropic", **kwargs)


__all__ = ["call_anthropic"]
