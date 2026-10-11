"""Compatibility wrapper for the Gemini provider adapter."""

from kurocode.core.llm import ask_llm


def call_gemini(prompt: str, **kwargs):
    return ask_llm(prompt, provider="gemini", **kwargs)


__all__ = ["call_gemini", "ask_llm"]
