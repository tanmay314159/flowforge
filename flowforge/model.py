"""The canonical, serializable workflow representation.

The model intentionally represents workflow structure as a hierarchy. UiPath
activities are nested in containers, while explicit connections are retained
for future flowchart support. Keeping both forms prevents the MVP from
pretending that every workflow is only a flat graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator


SCHEMA_VERSION = 1


class WorkflowError(ValueError):
    """Raised for an invalid builder operation."""


@dataclass
class Variable:
    name: str
    type: str
    scope: str = "root"
    default: Any = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "scope": self.scope,
        }
        if self.default is not None:
            value["default"] = self.default
        return value

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Variable":
        return cls(
            name=str(data["name"]),
            type=str(data["type"]),
            scope=str(data.get("scope", "root")),
            default=data.get("default"),
        )


@dataclass
class Argument:
    name: str
    type: str
    direction: str = "In"
    default: Any = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "direction": self.direction,
        }
        if self.default is not None:
            value["default"] = self.default
        return value

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Argument":
        return cls(
            name=str(data["name"]),
            type=str(data["type"]),
            direction=str(data.get("direction", "In")),
            default=data.get("default"),
        )


@dataclass
class ActivityNode:
    """A typed activity and its nested workflow children."""

    id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)
    children: list["ActivityNode"] = field(default_factory=list)
    # Branches are used by If today and can support TryCatch/Switch later.
    branches: dict[str, list["ActivityNode"]] = field(default_factory=dict)

    def add_child(self, child: "ActivityNode", branch: str = "body") -> None:
        if branch == "body":
            self.children.append(child)
        else:
            self.branches.setdefault(branch, []).append(child)

    def child_groups(self) -> Iterator[tuple[str, list["ActivityNode"]]]:
        if self.children:
            yield "body", self.children
        for name, children in self.branches.items():
            yield name, children

    def walk(self, parent_id: str | None = None, branch: str = "body") -> Iterator[tuple["ActivityNode", str | None, str]]:
        yield self, parent_id, branch
        for group_name, children in self.child_groups():
            for child in children:
                yield from child.walk(self.id, group_name)

    def find(self, node_id: str) -> "ActivityNode | None":
        for node, _, _ in self.walk():
            if node.id == node_id:
                return node
        return None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "properties": self.properties,
        }
        if self.children:
            value["children"] = [child.to_dict() for child in self.children]
        if self.branches:
            value["branches"] = {
                name: [child.to_dict() for child in children]
                for name, children in self.branches.items()
            }
        return value

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActivityNode":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            properties=dict(data.get("properties", {})),
            children=[cls.from_dict(child) for child in data.get("children", [])],
            branches={
                str(name): [cls.from_dict(child) for child in children]
                for name, children in data.get("branches", {}).items()
            },
        )


@dataclass
class Connection:
    """An explicit edge, useful for flowchart-style workflows."""

    from_id: str
    to_id: str

    def to_dict(self) -> dict[str, str]:
        return {"from_id": self.from_id, "to_id": self.to_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Connection":
        return cls(from_id=str(data["from_id"]), to_id=str(data["to_id"]))


@dataclass
class WorkflowProject:
    name: str
    template: str = "process"
    compatibility: str = "Windows"
    root: ActivityNode = field(default_factory=lambda: ActivityNode("root", "Sequence"))
    variables: list[Variable] = field(default_factory=list)
    arguments: list[Argument] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def find(self, node_id: str) -> ActivityNode | None:
        return self.root.find(node_id)

    def all_nodes(self) -> list[ActivityNode]:
        return [node for node, _, _ in self.root.walk()]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "template": self.template,
            "compatibility": self.compatibility,
            "root": self.root.to_dict(),
            "variables": [variable.to_dict() for variable in self.variables],
            "arguments": [argument.to_dict() for argument in self.arguments],
            "connections": [connection.to_dict() for connection in self.connections],
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowProject":
        version = data.get("schema_version", SCHEMA_VERSION)
        if version != SCHEMA_VERSION:
            raise WorkflowError(f"Unsupported workflow schema version: {version}")
        return cls(
            name=str(data["name"]),
            template=str(data.get("template", "process")),
            compatibility=str(data.get("compatibility", "Windows")),
            root=ActivityNode.from_dict(data.get("root", {"id": "root", "type": "Sequence"})),
            variables=[Variable.from_dict(item) for item in data.get("variables", [])],
            arguments=[Argument.from_dict(item) for item in data.get("arguments", [])],
            connections=[Connection.from_dict(item) for item in data.get("connections", [])],
            dependencies=dict(data.get("dependencies", {})),
            metadata=dict(data.get("metadata", {})),
        )
