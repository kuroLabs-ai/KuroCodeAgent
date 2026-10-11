"""Targeted cross-module integration and security tests for KuroAgent."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kurocode.core.task_state import TaskState, task_registry
from kurocode.core.verification import verification_engine
from kurocode.core.model_router import model_router, TaskType, ExecutionMetrics
from kurocode.core import memory, memory_db


class TestFullSystemIntegrity(unittest.TestCase):

    def test_task_state_persistence(self):
        """Verify task lifecycle state changes persist to SQLite."""
        task = task_registry.create(goal="Deploy service")
        self.assertEqual(task.state, TaskState.PENDING)
        self.assertTrue(task.mark_planning())
        self.assertTrue(task.mark_executing())
        self.assertTrue(task.mark_verifying("Checks passed"))
        self.assertTrue(task.mark_completed())
        self.assertTrue(task.is_terminal())

        persisted = memory_db.get_task(task.task_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted["state"], "completed")

    def test_memory_bridge_normalization(self):
        """Verify memory normalization between SQLite and JSON cache."""
        memory.save_memory("Test question", "Test response", metadata={"source": "test"})
        history = memory.load_memory()
        self.assertTrue(len(history) > 0)
        latest = history[-1]
        self.assertIn("user", latest)
        self.assertIn("assistant", latest)
        self.assertIn("user_text", latest)
        self.assertIn("assistant_text", latest)

    def test_verification_engine_strategies(self):
        """Verify individual verification strategies."""
        # Non-existent file verification
        v_res = verification_engine.verify_action(
            "write_file",
            tool_input={"path": "non_existent_file_xyz.txt", "content": "data"},
            tool_output={"success": True},
        )
        self.assertFalse(v_res.is_success)

        # Successful command check
        v_cmd = verification_engine.verify_action(
            "run_command",
            tool_input={"cmd": "echo test"},
            tool_output={"success": True, "returncode": 0, "stderr": ""},
        )
        self.assertTrue(v_cmd.is_success)

    def test_model_router_and_metrics(self):
        """Verify intent classification and metrics tracking."""
        prov, mod, t_type = model_router.select_route("Write a python script")
        self.assertEqual(t_type, TaskType.CODING)

        prov_v, mod_v, t_type_v = model_router.select_route("Describe photo", has_image=True)
        self.assertEqual(t_type_v, TaskType.VISION)

        metrics = ExecutionMetrics(task_id="task_full_test")
        metrics.record_tool_call()
        metrics.finish(success=True)
        self.assertEqual(metrics.tool_calls, 1)

    def test_encrypted_vault_lifecycle(self):
        """Verify Encrypted Credential Vault storage, masking, lock, and unlock."""
        from kurocode.core.vault import VaultManager, mask_secret
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_vault_path = Path(tmp_dir) / "test_vault.enc"
            v = VaultManager(vault_path=test_vault_path)
            
            # 1. Set secret
            self.assertTrue(v.set_secret("OPENAI_TEST_KEY", "sk-proj-1234567890abcdef1234567890", description="OpenAI API key"))
            self.assertEqual(v.get_secret("OPENAI_TEST_KEY"), "sk-proj-1234567890abcdef1234567890")
            
            # 2. Masking
            masked = mask_secret("sk-proj-1234567890abcdef1234567890")
            self.assertTrue(masked.startswith("sk-p"))
            self.assertTrue(masked.endswith("7890"))
            self.assertIn("****", masked)

            # 3. List secrets
            all_sec = v.list_secrets()
            self.assertEqual(len(all_sec), 1)
            self.assertEqual(all_sec[0]["key"], "OPENAI_TEST_KEY")

            # 4. Lock & Unlock
            v.lock()
            self.assertTrue(v.is_locked())
            self.assertIsNone(v.get_secret("OPENAI_TEST_KEY"))

            unlocked = v.unlock()
            self.assertTrue(unlocked)
            self.assertFalse(v.is_locked())
            self.assertEqual(v.get_secret("OPENAI_TEST_KEY"), "sk-proj-1234567890abcdef1234567890")

            # 5. Delete secret
            self.assertTrue(v.delete_secret("OPENAI_TEST_KEY"))
            self.assertIsNone(v.get_secret("OPENAI_TEST_KEY"))

    def test_sandbox_guard_and_ast_safety(self):
        """Verify AST code safety analysis, blocking dangerous operations, and safe interpreter execution."""
        from kurocode.core.sandbox import SandboxGuard
        from kurocode.tools.interpreter import execute_python_code

        guard = SandboxGuard()
        
        # 1. Safe code passes
        safe_code = "x = 10\ny = 20\nresult = x + y"
        rep_safe = guard.validate_python_code(safe_code)
        self.assertTrue(rep_safe.is_safe)
        self.assertEqual(rep_safe.risk_level, "SAFE")

        exec_res = execute_python_code(safe_code)
        self.assertTrue(exec_res["success"])
        self.assertEqual(exec_res["return_value"], 30)

        # 2. Dangerous imports blocked
        dangerous_code = "import _ctypes\nprint('pwned')"
        rep_danger = guard.validate_python_code(dangerous_code)
        self.assertFalse(rep_danger.is_safe)
        self.assertEqual(rep_danger.risk_level, "BLOCKED")

        exec_blocked = execute_python_code(dangerous_code)
        self.assertFalse(exec_blocked["success"])
        self.assertIn("SANDBOX GUARD BLOCKED", exec_blocked["stderr"])

        # 3. Destructive disk patterns blocked
        format_code = "import os\nos.system('format C:')"
        rep_format = guard.validate_python_code(format_code)
        self.assertFalse(rep_format.is_safe)
        self.assertEqual(rep_format.risk_level, "BLOCKED")

    def test_telegram_and_discord_integrations(self):
        """Verify Telegram and Discord integration registration, action routing, and error diagnostics."""
        from kurocode.integrations.telegram_integration import TelegramIntegration
        from kurocode.integrations.discord_integration import DiscordIntegration
        from kurocode.core.integration_manager import integration_manager

        # 1. Telegram integration abstraction
        tg = TelegramIntegration()
        self.assertEqual(tg.name, "telegram")
        self.assertEqual(tg.version, "2.0.0")

        # Telegram error explanation helper check
        explanation = tg._explain_error("Bad Request: chat not found", "@non_existent_channel")
        self.assertIn("was not found", explanation)

        explanation_admin = tg._explain_error("Bad Request: need administrator rights in the channel", "-100123456789")
        self.assertIn("Administrator", explanation_admin)

        # 2. Discord integration abstraction
        disc = DiscordIntegration()
        self.assertEqual(disc.name, "discord")

        # 3. Intent routing check
        tg_route = integration_manager.route_intent("Send alert to my telegram channel")
        self.assertIsNotNone(tg_route)
        self.assertEqual(tg_route.name, "telegram")

        disc_route = integration_manager.route_intent("Post summary to discord webhook")
        self.assertIsNotNone(disc_route)
        self.assertEqual(disc_route.name, "discord")

    def test_18_smart_notifier_and_diagnostics(self):
        """Verify smart multi-channel notifier and diagnostic inspector."""
        from unittest.mock import patch
        from kurocode.tools.notifier import send_smart_notification, diagnose_channel, NotificationUrgency

        with patch("kurocode.tools.notifier.load_notification_config", return_value={"discord_webhook": "https://example.invalid/webhook"}):
            with patch("kurocode.tools.notifier.send_discord_notification", return_value={"success": True}) as dispatch:
                res = send_smart_notification(
                    title="Unit Test Alert",
                    message="Testing multi-channel notification engine.",
                    urgency=NotificationUrgency.INFO,
                    channels=["discord"],
                )
        self.assertTrue(res.get("dispatched", {}).get("discord", {}).get("success"))
        dispatch.assert_called_once()

        diagnosis = diagnose_channel("unsupported")
        self.assertIn("error", diagnosis)


if __name__ == "__main__":
    unittest.main()
