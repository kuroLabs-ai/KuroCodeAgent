"""
tests/test_dual_interface.py — Tests for CLI Adapter and Mode Selection.
"""

import unittest
import json
from unittest.mock import MagicMock, patch

from kurocode.core.launch import parse_launch_args, LaunchArgs
from kurocode.core.io_bus import NullHost, QueueHost, CallbackHost, CoreEvent, InputRequest
from kurocode.adapters.cli import CLIAdapter


class TestCLIArchitecture(unittest.TestCase):

    def test_launch_args_parsing(self):
        # Default with no args -> CLI
        args = parse_launch_args([])
        self.assertEqual(args.mode, "cli")

        # Explicit --cli
        args_cli = parse_launch_args(["--cli"])
        self.assertEqual(args_cli.mode, "cli")

        # Headless query
        args_headless = parse_launch_args(["what time is it?"])
        self.assertEqual(args_headless.mode, "headless")
        self.assertEqual(args_headless.query, "what time is it?")

        # Headless with --json
        args_json = parse_launch_args(["/status", "--json"])
        self.assertEqual(args_json.mode, "headless")
        self.assertTrue(args_json.json_output)

    def test_cli_adapter_instantiation(self):
        cli = CLIAdapter()
        self.assertIsNotNone(cli.console)
        self.assertIsNotNone(cli.completer)

    def test_io_bus_queue_host(self):
        host = QueueHost()
        host.emit(CoreEvent(kind="log", message="test message", level="INFO"))
        drained = host.drain()
        self.assertEqual(len(drained), 1)
        self.assertEqual(drained[0]["message"], "test message")
        self.assertEqual(drained[0]["kind"], "log")

        # Subsequent drain should be empty
        self.assertEqual(len(host.drain()), 0)


if __name__ == "__main__":
    unittest.main()

