"""
tests/test_evolution.py — Test suite for KuroAgent Evolution Modules
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kurocode.core.paths import APP_DIR, USER_DATA_DIR, BRAIN_DIR, SKILLS_DIR, CONFIG_DIR
from kurocode.core.permissions import RiskLevel, PermissionGate
from kurocode.core.task_state import TaskState, task_registry
from kurocode.core.memory_types import memory_manager, ProceduralMemory
from kurocode.core.context_engine import context_engine
from kurocode.core.verification import verification_engine
from kurocode.core.plugin_registry import registry
from kurocode.core.project_aware import project_inspector
from kurocode.core.model_router import model_router, TaskType
from kurocode.core import config
from kurocode.core.llm import _call_openai_compatible


class TestKuroEvolution(unittest.TestCase):

    def test_01_paths_module(self):
        """Test central path resolution and AppData separation."""
        self.assertTrue(APP_DIR.exists())
        self.assertTrue(USER_DATA_DIR.exists())
        self.assertTrue(BRAIN_DIR.exists())
        self.assertTrue(SKILLS_DIR.exists())
        self.assertTrue(CONFIG_DIR.exists())

    def test_02_permissions_module(self):
        """Test risk levels and permission gate."""
        gate = PermissionGate(safe_mode=True)
        
        # Safe actions allowed automatically
        res_safe = gate.check("read_file", interactive=False)
        self.assertTrue(res_safe.allowed)
        self.assertEqual(res_safe.risk, RiskLevel.SAFE)

        # Confirm actions blocked non-interactively in safe mode
        res_confirm = gate.check("write_file", interactive=False)
        self.assertFalse(res_confirm.allowed)
        self.assertTrue(res_confirm.requires_confirmation)

        # Runtime overrides
        gate.allow_action("write_file")
        res_override = gate.check("write_file", interactive=False)
        self.assertTrue(res_override.allowed)

    def test_03_task_state_machine(self):
        """Test task lifecycle state transitions."""
        task = task_registry.create(goal="Build a test feature")
        self.assertEqual(task.state, TaskState.PENDING)

        self.assertTrue(task.mark_planning())
        self.assertEqual(task.state, TaskState.PLANNING)

        self.assertTrue(task.mark_executing())
        self.assertEqual(task.state, TaskState.EXECUTING)

        self.assertTrue(task.mark_verifying("All tests pass"))
        self.assertEqual(task.state, TaskState.VERIFYING)

        self.assertTrue(task.mark_completed())
        self.assertEqual(task.state, TaskState.COMPLETED)
        self.assertTrue(task.is_terminal())

    def test_04_memory_types_module(self):
        """Test Episodic, Semantic, Procedural, and Working memory."""
        # Working memory
        memory_manager.start_task("Deploy web service", task_id="t_123")
        self.assertEqual(memory_manager.working.goal, "Deploy web service")
        memory_manager.working.add_observation("Built React frontend successfully")
        self.assertIn("Built React frontend", memory_manager.working.to_context_str())

        # Semantic memory
        saved = memory_manager.save_fact(key="framework", value="React + Vite", category="project")
        self.assertTrue(saved)
        fact = memory_manager.get_fact("framework")
        self.assertIsNotNone(fact)
        self.assertEqual(fact.value, "React + Vite")

        # Procedural skill
        skill = ProceduralMemory(
            name="test_deploy",
            description="Deploy app to server",
            workflow="build -> verify -> push",
        )
        self.assertTrue(memory_manager.save_skill(skill))

    def test_05_context_engine(self):
        """Test intelligent context retrieval within token budget."""
        context = context_engine.build(
            user_input="Fix login component",
            task_goal="Fix login component",
            episode_limit=2,
        )
        self.assertIsInstance(context, str)

    def test_06_verification_engine(self):
        """Test verification strategies for file operations."""
        # Test non-existent file
        v_res = verification_engine.verify_action(
            "write_file",
            tool_input={"path": "non_existent_file_xyz_123.txt", "content": "hello"},
            tool_output={"success": True},
        )
        self.assertFalse(v_res.is_success)

    def test_07_plugin_registry(self):
        """Test plugin and tool contract registration."""
        def sample_tool(text=""):
            return {"success": True, "echo": text}

        contract = registry.register_function(
            name="test_echo",
            description="Echo test function",
            handler=sample_tool,
            risk_level=RiskLevel.SAFE,
        )
        self.assertTrue(registry.has_tool("test_echo"))

        res = registry.execute_tool("test_echo", {"text": "hello"})
        self.assertTrue(res["success"])
        self.assertEqual(res["echo"], "hello")

    def test_08_project_aware(self):
        """Test project profiling."""
        profile = project_inspector.inspect(".", force_refresh=True)
        self.assertTrue(len(profile.name) > 0)
        self.assertIn("Python", profile.languages)

    def test_09_model_router(self):
        """Test task classification and model routing."""
        provider, model, task_type = model_router.select_route("Fix bug in main.py script")
        self.assertEqual(task_type, TaskType.CODING)

    def test_10_integrations_manager(self):
        """Test external connected services (GitHub, Google Drive, Email)."""
        from kurocode.core.integration_manager import integration_manager
        integrations = integration_manager.list_integrations()
        names = [i["name"] for i in integrations]
        self.assertIn("github", names)
        self.assertIn("google_drive", names)
        self.assertIn("email", names)

        # Intent routing
        route_gh = integration_manager.route_intent("check my github repo")
        self.assertIsNotNone(route_gh)
        self.assertEqual(route_gh.name, "github")

        route_gd = integration_manager.route_intent("find the PDF on my Google Drive")
        self.assertIsNotNone(route_gd)
        self.assertEqual(route_gd.name, "google_drive")

        route_em = integration_manager.route_intent("check my unread emails")
        self.assertIsNotNone(route_em)
        self.assertEqual(route_em.name, "email")

    def test_11_llm_authorization_and_ollama_route(self):
        response = Mock(status_code=200)
        response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

        with patch("kurocode.core.llm.requests.post", return_value=response) as post:
            result = _call_openai_compatible(
                url="https://example.test/chat/completions",
                api_key="test-api-key",
                model="test-model",
                prompt="hello",
                system_prompt="be concise",
            )

        self.assertEqual(result, (True, "ok", 200))
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer test-api-key",
        )
        self.assertIn("ollama", config.PROVIDER_CHAIN)
        with patch.dict("os.environ", {"KURO_PROVIDER": "ollama"}):
            self.assertEqual(config.get_active_provider(), "ollama")
            self.assertIn("ollama", config.get_available_providers())


if __name__ == "__main__":
    unittest.main()
