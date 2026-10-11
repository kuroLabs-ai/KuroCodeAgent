"""Compatibility wrapper for the Groq provider adapter."""

from kurocode.core.llm import ask_llm


def call_groq(prompt: str, **kwargs):
    return ask_llm(prompt, provider="groq", **kwargs)


__all__ = ["call_groq", "ask_llm"]
