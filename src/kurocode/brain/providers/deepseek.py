"""Compatibility wrapper for the DeepSeek provider adapter."""

from kurocode.core.llm import ask_llm


def call_deepseek(prompt: str, **kwargs):
    return ask_llm(prompt, provider="deepseek", **kwargs)


__all__ = ["call_deepseek"]
