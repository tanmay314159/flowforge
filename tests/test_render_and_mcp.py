import json
import tempfile
import unittest
from pathlib import Path

from flowforge import WorkflowBuilder
from flowforge.mcp import FlowForgeMCPServer
from flowforge.render import render_project, render_xaml


class RenderAndMCPTests(unittest.TestCase):
    def test_render_is_deterministic_and_writes_project_files(self) -> None:
        builder = WorkflowBuilder.create_project("Render Test")
        builder.add_activity("ReadTextFile", {"path": "input.txt", "output": "content"})
        first = render_xaml(builder.project)
        second = render_xaml(builder.project)
        self.assertEqual(first, second)
        self.assertIn("ReadTextFile", first)
        with tempfile.TemporaryDirectory() as directory:
            paths = render_project(builder.project, directory)
            self.assertEqual({path.name for path in paths}, {"Main.xaml", "project.json", "flowforge.json"})
            self.assertTrue((Path(directory) / "Main.xaml").exists())

    def test_mcp_tool_lifecycle(self) -> None:
        server = FlowForgeMCPServer()
        initialized = server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}
        )
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "flowforge")
        created = server.call_tool("create_project", {"name": "MCP"})
        self.assertEqual(created["name"], "MCP")
        result = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "add_activity", "arguments": {"type": "Sequence"}},
            }
        )
        payload = json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(payload["activity_id"], "activity-1")
