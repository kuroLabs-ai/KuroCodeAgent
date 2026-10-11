import unittest
from unittest.mock import patch

from kurocode.core.agent import KuroAgent
from kurocode.core.paths import APP_DIR, BRAIN_DIR, DB_PATH, NOTES_DIR, USER_DATA_DIR


class TestKuroSelfAwareness(unittest.TestCase):
    def test_context_describes_identity_capabilities_and_limits(self):
        system_info = {
            "os": "TestOS",
            "os_release": "1",
            "python_version": "3",
            "cwd": str(APP_DIR),
            "user": "tester",
        }
        with (
            patch("kurocode.core.agent.personality.get_system_personality_prompt", return_value="KURO personality"),
            patch("kurocode.core.agent.get_system_info", return_value=system_info),
            patch("kurocode.core.agent.get_repo_tree", return_value="KuroAgent/"),
            patch("kurocode.core.agent.list_learned_skills", return_value=[]),
        ):
            context = KuroAgent()._build_system_context()

        self.assertIn("not a human or conscious being", context)
        self.assertIn(str(APP_DIR), context)
        self.assertIn(str(USER_DATA_DIR), context)
        self.assertIn(str(BRAIN_DIR), context)
        self.assertIn(str(DB_PATH), context)
        self.assertIn(str(NOTES_DIR), context)
        self.assertIn("write_file", context)
        self.assertIn("edit_file", context)
        self.assertIn("run relevant tests", context)
        self.assertIn("permission gate", context)
        self.assertIn("rebuilding and reinstalling is required", context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
