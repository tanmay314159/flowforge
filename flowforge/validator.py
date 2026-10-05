"""Static validation for the supported workflow subset."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .catalog import ACTIVITY_SPECS
from .model import ActivityNode, WorkflowProject


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    activity_id: str | None = None
    path: str | None = None
    fix_suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.activity_id is not None:
            value["activity_id"] = self.activity_id
        if self.path is not None:
            value["path"] = self.path
        if self.fix_suggestion is not None:
            value["fix_suggestion"] = self.fix_suggestion
        return value


@dataclass
class ValidationReport:
    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


_VARIABLE_REFERENCE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")


def _is_type(value: Any, expected: str) -> bool:
    if expected in {"string", "expression", "variable"}:
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "target":
        return isinstance(value, str) or (
            isinstance(value, dict) and isinstance(value.get("selector"), str)
        )
    return True


def _referenced_variables(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield from _VARIABLE_REFERENCE.findall(value)
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _referenced_variables(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _referenced_variables(nested)


def validate_project(project: WorkflowProject) -> ValidationReport:
    issues: list[ValidationIssue] = []
    if not project.name.strip():
        issues.append(
            ValidationIssue(
                "PROJECT_NAME_EMPTY",
                "Project name cannot be empty.",
                fix_suggestion="Set a non-empty project name.",
            )
        )
    if project.template not in {"process", "library"}:
        issues.append(
            ValidationIssue(
                "PROJECT_TEMPLATE_INVALID",
                f"Unsupported project template: {project.template}.",
                fix_suggestion="Use 'process' or 'library'.",
            )
        )
    if project.root.type != "Sequence" or project.root.id != "root":
        issues.append(
            ValidationIssue(
                "ROOT_INVALID",
                "The project root must be a Sequence with id 'root'.",
                activity_id=project.root.id,
                fix_suggestion="Create a root Sequence activity with id 'root'.",
            )
        )

    variables = {item.name: item for item in project.variables}
    arguments = {item.name: item for item in project.arguments}
    if len(variables) != len(project.variables):
        issues.append(ValidationIssue("DUPLICATE_VARIABLE", "Variable names must be unique."))
    if len(arguments) != len(project.arguments):
        issues.append(ValidationIssue("DUPLICATE_ARGUMENT", "Argument names must be unique."))
    overlap = set(variables) & set(arguments)
    for name in sorted(overlap):
        issues.append(
            ValidationIssue(
                "VARIABLE_ARGUMENT_COLLISION",
                f"'{name}' is declared as both a variable and an argument.",
                fix_suggestion="Rename one of the declarations.",
            )
        )

    seen: set[str] = set()
    node_parent: dict[str, str | None] = {}
    node_types: dict[str, str] = {}
    for node, parent_id, branch in project.root.walk():
        if node.id in seen:
            issues.append(
                ValidationIssue(
                    "DUPLICATE_ACTIVITY_ID",
                    f"Activity id is duplicated: {node.id}.",
                    activity_id=node.id,
                    fix_suggestion="Assign a unique id to every activity.",
                )
            )
        seen.add(node.id)
        node_parent[node.id] = parent_id
        node_types[node.id] = node.type
        spec = ACTIVITY_SPECS.get(node.type)
        if spec is None:
            issues.append(
                ValidationIssue(
                    "ACTIVITY_UNSUPPORTED",
                    f"Activity type is outside the MVP catalog: {node.type}.",
                    activity_id=node.id,
                    fix_suggestion="Use search_activities or add a catalog adapter for this activity.",
                )
            )
            continue
        for required in spec.required:
            if required not in node.properties or node.properties[required] in (None, ""):
                issues.append(
                    ValidationIssue(
                        "PROPERTY_REQUIRED",
                        f"Activity '{node.id}' requires property '{required}'.",
                        activity_id=node.id,
                        path=f"properties.{required}",
                        fix_suggestion=f"Set properties.{required}.",
                    )
                )
        for property_name, expected in spec.property_types.items():
            if property_name not in node.properties:
                continue
            value = node.properties[property_name]
            if not _is_type(value, expected):
                issues.append(
                    ValidationIssue(
                        "PROPERTY_TYPE_INVALID",
                        f"Property '{property_name}' on '{node.id}' must be a {expected}.",
                        activity_id=node.id,
                        path=f"properties.{property_name}",
                        fix_suggestion=f"Provide a value compatible with {expected}.",
                    )
                )
        if "target" in node.properties:
            target = node.properties["target"]
            if isinstance(target, dict) and not target.get("selector", "").strip():
                issues.append(
                    ValidationIssue(
                        "SELECTOR_EMPTY",
                        f"UI target for '{node.id}' has an empty selector.",
                        severity="warning",
                        activity_id=node.id,
                        path="properties.target.selector",
                        fix_suggestion="Capture a selector in the target application or provide a selector string.",
                    )
                )
        if spec.branches:
            for branch_name in node.branches:
                if branch_name not in spec.branches:
                    issues.append(
                        ValidationIssue(
                            "BRANCH_INVALID",
                            f"Branch '{branch_name}' is not supported by '{node.type}'.",
                            activity_id=node.id,
                            fix_suggestion=f"Use one of: {', '.join(spec.branches)}.",
                        )
                    )
        elif node.branches:
            issues.append(
                ValidationIssue(
                    "BRANCH_UNSUPPORTED",
                    f"Activity '{node.type}' cannot contain named branches.",
                    activity_id=node.id,
                    fix_suggestion="Move children to the activity body.",
                )
            )
        if not spec.container and (node.children or node.branches):
            issues.append(
                ValidationIssue(
                    "CHILDREN_NOT_ALLOWED",
                    f"Leaf activity '{node.id}' cannot contain child activities.",
                    activity_id=node.id,
                    fix_suggestion="Move nested activities under a Sequence or container.",
                )
            )
        for referenced in _referenced_variables(node.properties):
            if referenced not in variables and referenced not in arguments:
                issues.append(
                    ValidationIssue(
                        "VARIABLE_UNDEFINED",
                        f"Activity '{node.id}' references undefined name '{referenced}'.",
                        activity_id=node.id,
                        fix_suggestion=f"Create a variable or argument named '{referenced}'.",
                    )
                )
        for field_name in ("output", "variable"):
            reference = node.properties.get(field_name)
            if isinstance(reference, str) and reference and reference not in variables:
                issues.append(
                    ValidationIssue(
                        "VARIABLE_UNDEFINED",
                        f"Activity '{node.id}' writes to undefined variable '{reference}'.",
                        activity_id=node.id,
                        path=f"properties.{field_name}",
                        fix_suggestion=f"Create a variable named '{reference}'.",
                    )
                )

        if parent_id is not None and node_types.get(parent_id) == "If" and branch not in {"then", "else"}:
            issues.append(
                ValidationIssue(
                    "IF_BRANCH_INVALID",
                    f"Child '{node.id}' must belong to an If 'then' or 'else' branch.",
                    activity_id=node.id,
                )
            )

    connection_graph: dict[str, list[str]] = {}
    for edge in project.connections:
        if edge.from_id not in seen or edge.to_id not in seen:
            issues.append(
                ValidationIssue(
                    "CONNECTION_ENDPOINT_UNKNOWN",
                    f"Connection references an unknown activity: {edge.from_id} -> {edge.to_id}.",
                    fix_suggestion="Connect only existing activity ids.",
                )
            )
            continue
        connection_graph.setdefault(edge.from_id, []).append(edge.to_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            issues.append(
                ValidationIssue(
                    "CONNECTION_CYCLE",
                    f"Explicit activity connections contain a cycle at '{node_id}'.",
                    activity_id=node_id,
                    fix_suggestion="Remove the cycle or model it with a While activity.",
                )
            )
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for next_id in connection_graph.get(node_id, []):
            visit(next_id)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in connection_graph:
        visit(node_id)
    return ValidationReport(issues)
