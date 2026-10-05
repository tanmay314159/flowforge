"""Safe, explicit mutations over the workflow model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import ActivityNode, Argument, Connection, Variable, WorkflowError, WorkflowProject


class WorkflowBuilder:
    """Build a workflow through operations suitable for an agent tool layer."""

    def __init__(self, project: WorkflowProject):
        self.project = project
        self._next_id = self._discover_next_id()

    @classmethod
    def create_project(
        cls,
        name: str,
        template: str = "process",
        compatibility: str = "Windows",
    ) -> "WorkflowBuilder":
        return cls(WorkflowProject(name=name, template=template, compatibility=compatibility))

    @classmethod
    def load(cls, path: str | Path) -> "WorkflowBuilder":
        file_path = Path(path)
        with file_path.open("r", encoding="utf-8") as handle:
            return cls(WorkflowProject.from_dict(json.load(handle)))

    def save(self, path: str | Path) -> None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(self.project.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")

    def _discover_next_id(self) -> int:
        values: list[int] = []
        for node in self.project.all_nodes():
            if node.id.startswith("activity-"):
                suffix = node.id.removeprefix("activity-")
                if suffix.isdigit():
                    values.append(int(suffix))
        return max(values, default=0) + 1

    def _new_id(self) -> str:
        while self.project.find(f"activity-{self._next_id}") is not None:
            self._next_id += 1
        value = f"activity-{self._next_id}"
        self._next_id += 1
        return value

    def add_activity(
        self,
        activity_type: str,
        properties: dict[str, Any] | None = None,
        parent_id: str = "root",
        branch: str = "body",
        node_id: str | None = None,
    ) -> str:
        parent = self.project.find(parent_id)
        if parent is None:
            raise WorkflowError(f"Parent activity does not exist: {parent_id}")
        activity_id = node_id or self._new_id()
        if self.project.find(activity_id) is not None:
            raise WorkflowError(f"Activity id already exists: {activity_id}")
        if parent.type == "If" and branch == "body":
            branch = "then"
        if parent.type == "If" and branch not in {"then", "else"}:
            raise WorkflowError("If activities accept only the 'then' or 'else' branch")
        if parent.type != "If" and branch != "body":
            raise WorkflowError(f"Activity {parent_id} does not support named branches")
        node = ActivityNode(id=activity_id, type=activity_type, properties=dict(properties or {}))
        parent.add_child(node, branch)
        return activity_id

    def connect_activities(self, from_id: str, to_id: str) -> None:
        if self.project.find(from_id) is None:
            raise WorkflowError(f"Source activity does not exist: {from_id}")
        if self.project.find(to_id) is None:
            raise WorkflowError(f"Target activity does not exist: {to_id}")
        if from_id == to_id:
            raise WorkflowError("An activity cannot connect to itself")
        if any(edge.from_id == from_id and edge.to_id == to_id for edge in self.project.connections):
            return
        self.project.connections.append(Connection(from_id=from_id, to_id=to_id))

    def create_variable(
        self,
        name: str,
        type: str,
        scope: str = "root",
        default: Any = None,
    ) -> None:
        if any(item.name == name for item in self.project.variables):
            raise WorkflowError(f"Variable already exists: {name}")
        self.project.variables.append(Variable(name=name, type=type, scope=scope, default=default))

    def create_argument(
        self,
        name: str,
        type: str,
        direction: str = "In",
        default: Any = None,
    ) -> None:
        if any(item.name == name for item in self.project.arguments):
            raise WorkflowError(f"Argument already exists: {name}")
        self.project.arguments.append(
            Argument(name=name, type=type, direction=direction, default=default)
        )

    def set_metadata(self, key: str, value: Any) -> None:
        self.project.metadata[key] = value
