"""Compatibility wrapper for the Cloudflare Workers AI provider adapter."""

from kurocode.core.llm import ask_llm


def call_cloudflare(prompt: str, **kwargs):
    return ask_llm(prompt, provider="cloudflare", **kwargs)


__all__ = ["call_cloudflare"]
