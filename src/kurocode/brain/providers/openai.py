"""Compatibility wrapper for the OpenAI provider adapter."""

from kurocode.core.llm import ask_llm


def call_openai(prompt: str, **kwargs):
    return ask_llm(prompt, provider="openai", **kwargs)


__all__ = ["call_openai", "ask_llm"]
