"""Compatibility wrapper for secret management."""

from kurocode.core.vault import VaultManager, mask_secret, vault

__all__ = ["VaultManager", "mask_secret", "vault"]
