"""Compatibility wrapper for the xAI (Grok) provider adapter."""

from kurocode.core.llm import ask_llm


def call_xai(prompt: str, **kwargs):
    return ask_llm(prompt, provider="xai", **kwargs)


__all__ = ["call_xai"]
