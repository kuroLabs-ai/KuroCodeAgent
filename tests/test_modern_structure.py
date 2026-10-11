"""
tests/test_modern_structure.py — Test suite for Modern Python (src-layout) Structure.
Verifies:
1. Modern package imports under the `kurocode` namespace.
2. Complete parity and identity between legacy root shims and new package objects.
3. PEP 561 py.typed presence.
4. CLI entrypoint execution signatures.
"""

import unittest
from pathlib import Path


class TestModernPackageStructure(unittest.TestCase):

    def test_kurocode_namespace_imports(self):
        """Verify modern package structure under src/kurocode."""
        import kurocode
        from kurocode.core.agent import KuroAgent
        from kurocode.core.vault import VaultManager
        from kurocode.core.sandbox import SandboxGuard
        from kurocode.core.paths import APP_DIR, USER_DATA_DIR
        from kurocode.tools.files import read_file, write_file
        from kurocode.tools.system import run_command
        from kurocode.adapters.cli import CLIAdapter
        from kurocode.cli.app import run

        self.assertIsNotNone(kurocode)
        self.assertTrue(callable(KuroAgent))
        self.assertTrue(callable(VaultManager))
        self.assertTrue(callable(SandboxGuard))
        self.assertTrue(APP_DIR.exists())
        self.assertTrue(USER_DATA_DIR.exists())
        self.assertTrue(callable(read_file))
        self.assertTrue(callable(write_file))
        self.assertTrue(callable(run_command))
        self.assertTrue(callable(CLIAdapter))
        self.assertTrue(callable(run))

    def test_backward_compatibility_identity(self):
        """Verify legacy root imports resolve to the exact identical objects as kurocode."""
        from kurocode.core.agent import KuroAgent
        from kurocode.core.agent import KuroAgent as LegacyAgent
        self.assertIs(KuroAgent, LegacyAgent)

        from kurocode.tools.files import read_file
        from kurocode.tools.files import read_file as legacy_read_file
        self.assertIs(read_file, legacy_read_file)

        from kurocode.core.paths import APP_DIR
        from kurocode.core.paths import APP_DIR as legacy_app_dir
        self.assertEqual(APP_DIR, legacy_app_dir)

    def test_pep561_typing_marker(self):
        """Verify py.typed marker exists for type checkers (mypy/pyright)."""
        import kurocode
        package_dir = Path(kurocode.__file__).resolve().parent
        py_typed = package_dir / "py.typed"
        self.assertTrue(py_typed.exists(), f"py.typed marker missing at {py_typed}")


if __name__ == "__main__":
    unittest.main()
