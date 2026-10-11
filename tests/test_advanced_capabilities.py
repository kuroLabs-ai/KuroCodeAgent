"""
tests/test_advanced_capabilities.py — Test suite for Kuro 2.0 advanced subsystems:
1. Self-Healing subsystem (detector, diagnostician, retry, repairer, rollback, engine)
2. Controlled Self-Improvement subsystem (analyzer, improver, tester, ledger, engine)
3. Dynamic Tool Generation (AST safety, runtime compilation, hot-registration)
4. Integrations Registry & GitLab Integration
5. Plugins Subsystem (installer, manager, source install)
6. Modular Skills Management (manifest install, listing, deletion)
7. User Profile Separation
"""

import sys
import unittest
import tempfile
import json
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestSelfHealingSubsystem(unittest.TestCase):
    """Verifies all components of the dedicated self-healing package."""

    def test_detector_categories(self):
        from kurocode.healing.detector import FailureDetector, ErrorCategory, FailureSeverity

        detector = FailureDetector()

        # Missing module
        r1 = detector.classify("ModuleNotFoundError: No module named 'rich'", tool_name="test_tool")
        self.assertEqual(r1.category, ErrorCategory.MISSING_DEPENDENCY)
        self.assertEqual(r1.severity, FailureSeverity.MEDIUM)
        self.assertEqual(r1.missing_module, "rich")

        # Syntax error
        r2 = detector.classify("SyntaxError: invalid syntax (<string>, line 1)", tool_name="test_tool")
        self.assertEqual(r2.category, ErrorCategory.SYNTAX_ERROR)

        # Missing file/directory
        r3 = detector.classify("FileNotFoundError: [Errno 2] No such file or directory: 'foo/bar'", tool_name="test_tool")
        self.assertEqual(r3.category, ErrorCategory.FILE_SYSTEM_ERROR)

        # Tool result dict classification
        r4 = detector.detect_from_tool_result("cmd_tool", {"success": False, "error": "Access is denied"})
        self.assertIsNotNone(r4)
        self.assertEqual(r4.category, ErrorCategory.PERMISSION_DENIED)

    def test_diagnostician(self):
        from kurocode.healing.detector import FailureDetector
        from kurocode.healing.diagnostician import FailureDiagnostician

        detector = FailureDetector()
        diagnostician = FailureDiagnostician()

        report = detector.classify("ModuleNotFoundError: No module named 'requests'", tool_name="pip_tool")
        diagnosis = diagnostician.diagnose(report)

        self.assertIn("requests", diagnosis.root_cause)
        self.assertTrue(diagnosis.can_auto_heal)
        self.assertTrue(len(diagnosis.repair_plan) > 0)

    def test_retry_policy(self):
        from kurocode.healing.retry import RetryPolicy

        policy = RetryPolicy(max_attempts=3, initial_delay=0.1, backoff_factor=2.0, jitter=False)
        self.assertEqual(policy.max_attempts, 3)

        delay0 = policy.calculate_delay(0)
        delay1 = policy.calculate_delay(1)
        self.assertAlmostEqual(delay0, 0.1)
        self.assertAlmostEqual(delay1, 0.2)

        # Test execute_with_retry success
        counter = {"attempts": 0}

        def flaky_func():
            counter["attempts"] += 1
            if counter["attempts"] < 2:
                raise ValueError("Transient error")
            return "success"

        result = policy.execute_with_retry(flaky_func)
        self.assertEqual(result, "success")
        self.assertEqual(counter["attempts"], 2)

    def test_repairer_missing_dir(self):
        from kurocode.healing.detector import FailureReport, ErrorCategory, FailureSeverity
        from kurocode.healing.diagnostician import Diagnosis
        from kurocode.healing.repairer import HealingRepairer

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "subfolder" / "nested" / "file.txt"
            report = FailureReport(
                category=ErrorCategory.FILE_SYSTEM_ERROR,
                severity=FailureSeverity.MEDIUM,
                message="File not found",
                target_path=str(target_dir),
            )
            diag = Diagnosis(
                report=report,
                root_cause=f"File {target_dir} not found",
                suggested_action="Create missing directories",
                confidence=0.9,
                can_auto_heal=True,
            )
            repairer = HealingRepairer()
            res = repairer.attempt_repair(diag)
            self.assertTrue(res.get("success"), res.get("error"))
            self.assertTrue(target_dir.parent.exists())

    def test_rollback_manager(self):
        from kurocode.healing.rollback import RollbackManager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "sample.txt"
            test_file.write_text("initial content", encoding="utf-8")

            manager = RollbackManager(backup_dir=Path(tmpdir) / "backups")
            bak_path = manager.backup_file(test_file)
            self.assertIsNotNone(bak_path)
            self.assertTrue(bak_path.exists())

            # Corrupt file
            test_file.write_text("corrupted content", encoding="utf-8")
            self.assertEqual(test_file.read_text(encoding="utf-8"), "corrupted content")

            # Restore file
            restored = manager.rollback_file(test_file)
            self.assertTrue(restored)
            self.assertEqual(test_file.read_text(encoding="utf-8"), "initial content")

    def test_healing_engine_facade(self):
        from kurocode.healing import healing_engine

        res = healing_engine.auto_heal("sample_tool", "FileNotFoundError: No such file or directory: 'non_existent_dir/foo'")
        self.assertIn("success", res)


class TestControlledSelfImprovementSubsystem(unittest.TestCase):
    """Verifies all components of the controlled self-improvement package."""

    def test_analyzer_and_improver(self):
        from kurocode.evolution.analyzer import EvolutionAnalyzer
        from kurocode.evolution.improver import EvolutionImprover

        analyzer = EvolutionAnalyzer()
        patterns = analyzer.analyze_execution_patterns([
            {"tool": "read_file", "success": True, "duration": 0.05},
            {"tool": "read_file", "success": True, "duration": 0.04},
        ])
        self.assertIsInstance(patterns, list)

        improver = EvolutionImprover()
        proposal = improver.propose_improvement(
            target_module="kurocode.tools.files",
            rationale="Add caching layer for frequent read_file calls",
            action="refactor",
        )
        self.assertTrue(proposal.proposal_id.startswith("PROP-"))
        self.assertEqual(proposal.action, "refactor")

    def test_tester_ast_safety(self):
        from kurocode.evolution.tester import EvolutionTester

        tester = EvolutionTester()

        safe_code = """
def calculate_sum(a: int, b: int) -> int:
    return a + b
"""
        unsafe_code = """
import os
os.system("format C:")
"""
        self.assertTrue(tester.validate_ast_safety(safe_code))
        self.assertFalse(tester.validate_ast_safety(unsafe_code))

    def test_ledger_versioning(self):
        from kurocode.evolution.improver import ImprovementProposal
        from kurocode.evolution.versioning import EvolutionLedger

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = Path(tmpdir) / "history.json"
            ledger = EvolutionLedger(history_file=ledger_path)

            prop = ImprovementProposal(
                proposal_id="PROP-TEST-01",
                target_module="kurocode.core.agent",
                action="optimize",
                rationale="Optimize context builder",
            )
            ledger.record_proposal(prop)

            history = ledger.get_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["proposal_id"], "PROP-TEST-01")

    def test_evolution_engine_cycle(self):
        from kurocode.evolution import evolution_engine

        result = evolution_engine.run_evolution_cycle()
        self.assertIn("success", result)


class TestDynamicToolGeneration(unittest.TestCase):
    """Verifies dynamic tool generation, AST safety, and hot-registration."""

    def test_generate_and_register_safe_tool(self):
        from kurocode.tools.generator import DynamicToolGenerator
        from kurocode.core.plugin_registry import registry

        gen = DynamicToolGenerator()
        code = """
def custom_math_adder(x: int, y: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return x + y
"""
        res = gen.generate_and_register(
            name="custom_math_adder",
            description="Adds two integers dynamically",
            code_body=code,
            persist=False,
        )

        self.assertTrue(res.get("success"), res.get("error"))
        self.assertEqual(res.get("tool_name"), "custom_math_adder")

        # Verify execution via registry
        tool_entry = registry.get("custom_math_adder")
        self.assertIsNotNone(tool_entry)
        self.assertEqual(tool_entry.func(2, 3), 5)

    def test_reject_unsafe_dynamic_tool(self):
        from kurocode.tools.generator import DynamicToolGenerator

        gen = DynamicToolGenerator()
        unsafe_code = """
import ctypes
def evil_tool():
    ctypes.windll.kernel32.ExitProcess(0)
"""
        res = gen.generate_and_register(
            name="evil_tool",
            description="Dangerous tool",
            code_body=unsafe_code,
            persist=False,
        )
        self.assertFalse(res.get("success"))
        self.assertIn("Security violation", res.get("error", ""))


class TestIntegrationsSubsystem(unittest.TestCase):
    """Verifies GitLab integration and integration registry."""

    def test_gitlab_integration(self):
        from kurocode.integrations.gitlab_integration import GitLabIntegration

        gitlab = GitLabIntegration(token="dummy-token", base_url="https://gitlab.example.com")
        self.assertEqual(gitlab.name, "gitlab")
        self.assertTrue(gitlab.is_connected)

        status = gitlab.health_check()
        self.assertTrue(status.get("connected"))

    def test_integration_registry(self):
        from kurocode.integrations.registry import IntegrationRegistry
        from kurocode.integrations.gitlab_integration import GitLabIntegration

        reg = IntegrationRegistry()
        gl = GitLabIntegration()
        reg.register("gitlab_custom", gl)

        retrieved = reg.get("gitlab_custom")
        self.assertIsNotNone(retrieved)


class TestPluginsAndSkillsSubsystems(unittest.TestCase):
    """Verifies plugin installation and modular skills management."""

    def test_plugin_install_from_source(self):
        from kurocode.plugins.manager import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "installed_plugins"
            plugins_dir.mkdir()

            # Create a mock plugin source directory
            src_dir = Path(tmpdir) / "my_plugin_src"
            src_dir.mkdir()
            manifest = {
                "name": "test_echo_plugin",
                "version": "1.0.0",
                "description": "Echo test plugin",
                "entrypoint": "main.py",
            }
            (src_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
            (src_dir / "main.py").write_text("print('test plugin loaded')", encoding="utf-8")

            mgr = PluginManager(plugins_dir=plugins_dir)
            res = mgr.install_from_source(str(src_dir))
            self.assertTrue(res.get("success"), res.get("error"))

            installed = mgr.list_plugins()
            names = [p["name"] for p in installed]
            self.assertIn("test_echo_plugin", names)

    def test_skill_install_and_listing(self):
        from kurocode.tools.self_improve import install_skill, list_learned_skills, delete_skill

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock skill directory with skill.json
            skill_src = Path(tmpdir) / "docker_deploy_skill"
            skill_src.mkdir()
            manifest = {
                "name": "docker_deploy_test",
                "description": "Deploys application using Docker Compose",
                "version": "1.0.0",
            }
            (skill_src / "skill.json").write_text(json.dumps(manifest), encoding="utf-8")
            (skill_src / "README.md").write_text("# Docker Deploy Test\nRun docker compose up -d", encoding="utf-8")

            res = install_skill(str(skill_src))
            self.assertTrue(res.get("success"), res.get("error"))

            # Verify listed
            skills = list_learned_skills()
            names = [s["name"] for s in skills]
            self.assertIn("docker_deploy_test", names)

            # Cleanup
            deleted = delete_skill("docker_deploy_test")
            self.assertTrue(deleted)


class TestUserProfileSeparation(unittest.TestCase):
    """Verifies runtime user profile isolation."""

    def test_user_profile_paths(self):
        from kurocode.core.paths import USER_PROFILE_DIR, get_user_profile_dir

        expected_home = Path.home() / ".kurocode"
        self.assertEqual(USER_PROFILE_DIR, expected_home)

        profile_dir = get_user_profile_dir()
        self.assertIsInstance(profile_dir, Path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
