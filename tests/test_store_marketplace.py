"""
tests/test_store_marketplace.py — Test suite for Kuro Puzzle Store & Hub.
Verifies catalog, search, one-click install/remove, and agent autonomous self-extension.
"""

import sys
import unittest
import tempfile
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestStoreMarketplace(unittest.TestCase):
    """Tests the Kuro capability store, catalog, and install/remove lifecycle."""

    def setUp(self):
        from kurocode.store import StoreManager
        self.tmpdir = tempfile.TemporaryDirectory()
        self.catalog_file = Path(self.tmpdir.name) / "test_store_catalog.json"
        self.manager = StoreManager(catalog_file=self.catalog_file)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_01_catalog_and_categories(self):
        items = self.manager.get_catalog()
        self.assertGreater(len(items), 0)

        # Check all puzzle-piece categories are present
        types = {i.item_type.value for i in items}
        self.assertIn("tool", types)
        self.assertIn("plugin", types)
        self.assertIn("skill", types)
        self.assertIn("integration", types)

    def test_02_store_search(self):
        # Search by tag or keyword
        res_json = self.manager.search("json")
        self.assertTrue(any(i.name == "json_inspector" for i in res_json))

        res_crypto = self.manager.search("crypto")
        self.assertTrue(any(i.name == "hash_calculator" for i in res_crypto))

        res_tdd = self.manager.search("tdd")
        self.assertTrue(any(i.name == "tdd_refactoring" for i in res_tdd))

    def test_03_install_and_execute_tool_piece(self):
        from kurocode.core.plugin_registry import registry

        # Install json_inspector tool
        install_res = self.manager.install("json_inspector")
        self.assertTrue(install_res.get("success"), install_res.get("error"))

        # Verify tool is registered and functional
        tool = registry.get("json_inspector")
        self.assertIsNotNone(tool)
        output = tool.func('{"hello": "world"}')
        self.assertTrue(output.get("success"))
        self.assertTrue(output.get("valid"))

    def test_04_install_and_execute_skill_piece(self):
        from kurocode.tools.self_improve import list_learned_skills

        install_res = self.manager.install("tdd_refactoring")
        self.assertTrue(install_res.get("success"), install_res.get("error"))

        skills = list_learned_skills()
        names = [s["name"] for s in skills]
        self.assertIn("tdd_refactoring", names)

    def test_05_publish_and_install_custom_piece(self):
        # Publish custom piece as agent or user
        pub_res = self.manager.publish(
            name="cube_number",
            item_type="tool",
            description="Calculates cube of an integer",
            payload={
                "code": "def cube_number(n: int) -> dict:\n    return {'success': True, 'result': n ** 3}\n",
                "entrypoint": "cube_number",
            },
            author="Autonomous Kuro Agent",
            tags=["math", "custom"],
        )
        self.assertTrue(pub_res.get("success"))

        # Verify custom piece is listed in catalog
        item = self.manager.get_item("cube_number")
        self.assertIsNotNone(item)
        self.assertEqual(item.author, "Autonomous Kuro Agent")

        # Install and test execution
        inst = self.manager.install("cube_number")
        self.assertTrue(inst.get("success"))

        from kurocode.core.plugin_registry import registry
        tool = registry.get("cube_number")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.func(3)["result"], 27)

    def test_06_remove_piece(self):
        from kurocode.core.plugin_registry import registry

        # Install
        self.manager.install("base64_codec")
        self.assertTrue(registry.has_tool("base64_codec"))

        # Remove
        rem_res = self.manager.remove("base64_codec")
        self.assertTrue(rem_res.get("success"))
        self.assertFalse(registry.has_tool("base64_codec"))

    def test_07_remote_sync_mock(self):
        from unittest.mock import patch, MagicMock
        import io

        mock_catalog_data = b"""[
            {
                "name": "remote_echo_tool",
                "item_type": "tool",
                "description": "Echoes back input from remote hub",
                "author": "kuroLabs-ai",
                "payload": {"code": "def echo(x): return {'out': x}", "entrypoint": "echo"}
            }
        ]"""

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_catalog_data
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            sync_res = self.manager.update_from_remote("https://raw.githubusercontent.com/kuroLabs-ai/hub/main/catalog.json")
            self.assertTrue(sync_res.get("success"))
            self.assertEqual(sync_res.get("count"), 1)

            # Verify it is in catalog
            item = self.manager.get_item("remote_echo_tool")
            self.assertIsNotNone(item)
            self.assertEqual(item.author, "kuroLabs-ai")

    def test_08_install_from_url_with_ast_safety(self):
        from unittest.mock import patch, MagicMock

        # Safe online code
        safe_code = b"""def safe_math(a: int, b: int) -> dict:
    return {'sum': a + b}
"""
        mock_resp = MagicMock()
        mock_resp.read.return_value = safe_code
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = self.manager.install_from_url("https://raw.githubusercontent.com/kuroLabs-ai/hub/main/tools/safe_math.py")
            self.assertTrue(res.get("success"), res.get("error"))

        # Unsafe online code rejected by AST safety scanner
        unsafe_code = b"""import _ctypes
def dangerous():
    pass
"""
        mock_unsafe_resp = MagicMock()
        mock_unsafe_resp.read.return_value = unsafe_code
        mock_unsafe_resp.__enter__.return_value = mock_unsafe_resp

        with patch("urllib.request.urlopen", return_value=mock_unsafe_resp):
            bad_res = self.manager.install_from_url("https://raw.githubusercontent.com/kuroLabs-ai/hub/main/tools/danger.py")
            self.assertFalse(bad_res.get("success"))
            self.assertIn("rejected", bad_res.get("error"))

    def test_09_install_piece_with_separate_file_path(self):
        # 1. Publish or load item with separate file_path (no embedded code in JSON)
        self.manager.publish(
            name="currency_converter",
            item_type="tool",
            description="Currency conversion tool",
            payload={"entrypoint": "currency_converter"},
        )
        item = self.manager.get_item("currency_converter")
        self.assertIsNotNone(item)
        item.file_path = "tools/currency_converter.py"

        # 2. Install - StoreManager resolves the separate file community_hub/tools/currency_converter.py
        res = self.manager.install("currency_converter")
        self.assertTrue(res.get("success"), res.get("error"))

        # 3. Verify tool is loaded and functional
        from kurocode.core.plugin_registry import registry
        tool = registry.get("currency_converter")
        self.assertIsNotNone(tool)
        output = tool.func(100.0, "USD", "EUR")
        self.assertTrue(output.get("success"))
        self.assertEqual(output.get("result"), 92.0)


class TestAgentAutonomousSelfExtension(unittest.TestCase):
    """Tests that the agent can autonomously search, install, and author tools/plugins/skills."""

    def test_agent_has_store_and_creation_tools(self):
        from kurocode.core.agent import KuroAgent
        from kurocode.core.plugin_registry import registry

        agent = KuroAgent()

        # Check self-extension tools are registered
        self.assertTrue(registry.has_tool("store_search"))
        self.assertTrue(registry.has_tool("store_install"))
        self.assertTrue(registry.has_tool("store_list"))
        self.assertTrue(registry.has_tool("store_publish"))
        self.assertTrue(registry.has_tool("store_update"))
        self.assertTrue(registry.has_tool("create_tool"))
        self.assertTrue(registry.has_tool("create_plugin"))
        self.assertTrue(registry.has_tool("create_skill"))

        # Test agent executing store search
        search_res = agent.execute_tool({"action": "store_search", "query": "hash"}, interactive=False)
        self.assertIn("results", search_res)
        self.assertTrue(len(search_res["results"]) > 0)

        # Test agent autonomous skill creation
        from kurocode.core.permissions import default_gate
        prev_gate_safe = default_gate.safe_mode
        default_gate.set_safe_mode(False)
        try:
            skill_res = agent.execute_tool({
                "action": "create_skill",
                "name": "git_bisect_flow",
                "description": "Routine for automated git bisect regression hunt",
                "steps": ["git bisect start", "git bisect bad", "git bisect good v1.0", "run test", "git bisect reset"],
            }, interactive=False)
            self.assertTrue(skill_res.get("success"), skill_res.get("error"))
        finally:
            default_gate.set_safe_mode(prev_gate_safe)


if __name__ == "__main__":
    unittest.main(verbosity=2)
