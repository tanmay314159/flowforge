"""A small stdio JSON-RPC server exposing the FlowForge tools.

The transport intentionally has no third-party dependency. It implements the
MCP methods needed by clients to discover and call the MVP tools.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

from .builder import WorkflowBuilder
from .catalog import search_activities
from .model import WorkflowError
from .render import render_project
from .validator import validate_project


def _text_result(value: Any, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": json.dumps(value, indent=2, sort_keys=True)}]
    }
    if is_error:
        result["isError"] = True
    return result


TOOL_DEFINITIONS = [
    {
        "name": "create_project",
        "description": "Create an empty FlowForge workflow project.",
        "inputSchema": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "template": {"type": "string", "enum": ["process", "library"]},
                "compatibility": {"type": "string"},
            },
        },
    },
    {
        "name": "load_project",
        "description": "Load a FlowForge JSON project from disk.",
        "inputSchema": {"type": "object", "required": ["project_path"], "properties": {"project_path": {"type": "string"}}},
    },
    {
        "name": "search_activities",
        "description": "Find supported activities and their typed properties.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "default": ""}}},
    },
    {
        "name": "add_activity",
        "description": "Add an activity under a container or If branch.",
        "inputSchema": {
            "type": "object",
            "required": ["type"],
            "properties": {
                "type": {"type": "string"},
                "properties": {"type": "object"},
                "parent_id": {"type": "string", "default": "root"},
                "branch": {"type": "string", "default": "body"},
                "node_id": {"type": "string"},
            },
        },
    },
    {
        "name": "connect_activities",
        "description": "Add an explicit flowchart edge between activities.",
        "inputSchema": {
            "type": "object",
            "required": ["from_id", "to_id"],
            "properties": {"from_id": {"type": "string"}, "to_id": {"type": "string"}},
        },
    },
    {
        "name": "create_variable",
        "description": "Declare a workflow variable.",
        "inputSchema": {
            "type": "object",
            "required": ["name", "type"],
            "properties": {"name": {"type": "string"}, "type": {"type": "string"}, "scope": {"type": "string"}, "default": {}} ,
        },
    },
    {
        "name": "create_argument",
        "description": "Declare a workflow argument.",
        "inputSchema": {
            "type": "object",
            "required": ["name", "type"],
            "properties": {"name": {"type": "string"}, "type": {"type": "string"}, "direction": {"type": "string"}, "default": {}},
        },
    },
    {
        "name": "validate_workflow",
        "description": "Run static validation and return machine-readable issues.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "save_project",
        "description": "Save the current project as FlowForge JSON.",
        "inputSchema": {"type": "object", "required": ["project_path"], "properties": {"project_path": {"type": "string"}}},
    },
    {
        "name": "render_project",
        "description": "Write Main.xaml, project.json, and flowforge.json to a directory.",
        "inputSchema": {"type": "object", "required": ["output_dir"], "properties": {"output_dir": {"type": "string"}}},
    },
]


class FlowForgeMCPServer:
    def __init__(self) -> None:
        self.builder: WorkflowBuilder | None = None

    def _require_builder(self) -> WorkflowBuilder:
        if self.builder is None:
            raise WorkflowError("No project is loaded. Call create_project or load_project first.")
        return self.builder

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "create_project":
            self.builder = WorkflowBuilder.create_project(
                name=arguments["name"],
                template=arguments.get("template", "process"),
                compatibility=arguments.get("compatibility", "Windows"),
            )
            return self.builder.project.to_dict()
        if name == "load_project":
            self.builder = WorkflowBuilder.load(arguments["project_path"])
            return self.builder.project.to_dict()
        if name == "search_activities":
            return {"activities": search_activities(arguments.get("query", ""))}
        builder = self._require_builder()
        if name == "add_activity":
            activity_id = builder.add_activity(
                arguments["type"],
                arguments.get("properties"),
                arguments.get("parent_id", "root"),
                arguments.get("branch", "body"),
                arguments.get("node_id"),
            )
            return {"activity_id": activity_id, "project": builder.project.to_dict()}
        if name == "connect_activities":
            builder.connect_activities(arguments["from_id"], arguments["to_id"])
            return builder.project.to_dict()
        if name == "create_variable":
            builder.create_variable(
                arguments["name"], arguments["type"], arguments.get("scope", "root"), arguments.get("default")
            )
            return builder.project.to_dict()
        if name == "create_argument":
            builder.create_argument(
                arguments["name"], arguments["type"], arguments.get("direction", "In"), arguments.get("default")
            )
            return builder.project.to_dict()
        if name == "validate_workflow":
            return validate_project(builder.project).to_dict()
        if name == "save_project":
            builder.save(arguments["project_path"])
            return {"saved": arguments["project_path"]}
        if name == "render_project":
            paths = render_project(builder.project, arguments["output_dir"])
            return {"files": [str(path) for path in paths]}
        raise KeyError(f"Unknown tool: {name}")

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": request.get("params", {}).get("protocolVersion", "2024-11-05"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "flowforge", "version": "0.1.0"},
                },
            }
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOL_DEFINITIONS}}
        if method == "tools/call":
            params = request.get("params", {})
            try:
                result = self.call_tool(params["name"], params.get("arguments", {}))
                return {"jsonrpc": "2.0", "id": request_id, "result": _text_result(result)}
            except (KeyError, TypeError, ValueError, OSError, WorkflowError) as exc:
                return {"jsonrpc": "2.0", "id": request_id, "result": _text_result({"error": str(exc)}, True)}
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    def serve_forever(self) -> None:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
                response = self.handle(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError as exc:
                response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


def serve() -> None:
    FlowForgeMCPServer().serve_forever()
