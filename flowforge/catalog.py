"""The deliberately small, typed activity catalog used by the MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActivitySpec:
    type: str
    category: str
    required: tuple[str, ...] = ()
    property_types: dict[str, str] = field(default_factory=dict)
    container: bool = False
    branches: tuple[str, ...] = ()
    description: str = ""


ACTIVITY_SPECS: dict[str, ActivitySpec] = {
    "Sequence": ActivitySpec(
        "Sequence", "Control Flow", container=True, description="Runs child activities in order."
    ),
    "UseApplicationBrowser": ActivitySpec(
        "UseApplicationBrowser",
        "UI",
        property_types={"url": "string", "application": "string"},
        container=True,
        description="Scopes UI activities to an application or browser.",
    ),
    "Click": ActivitySpec(
        "Click",
        "UI",
        required=("target",),
        property_types={"target": "target", "timeout": "number"},
    ),
    "TypeInto": ActivitySpec(
        "TypeInto",
        "UI",
        required=("target", "text"),
        property_types={"target": "target", "text": "string", "timeout": "number"},
    ),
    "GetText": ActivitySpec(
        "GetText",
        "UI",
        required=("target", "output"),
        property_types={"target": "target", "output": "variable", "timeout": "number"},
    ),
    "If": ActivitySpec(
        "If",
        "Control Flow",
        required=("condition",),
        property_types={"condition": "string"},
        container=True,
        branches=("then", "else"),
    ),
    "ForEach": ActivitySpec(
        "ForEach",
        "Control Flow",
        required=("item", "in"),
        property_types={"item": "string", "in": "string"},
        container=True,
    ),
    "While": ActivitySpec(
        "While",
        "Control Flow",
        required=("condition",),
        property_types={"condition": "string"},
        container=True,
    ),
    "Assign": ActivitySpec(
        "Assign",
        "Data",
        required=("variable", "value"),
        property_types={"variable": "variable", "value": "expression"},
    ),
    "ReadTextFile": ActivitySpec(
        "ReadTextFile",
        "Files",
        required=("path", "output"),
        property_types={"path": "string", "output": "variable"},
    ),
    "WriteTextFile": ActivitySpec(
        "WriteTextFile",
        "Files",
        required=("path", "text"),
        property_types={"path": "string", "text": "expression"},
    ),
    "HttpRequest": ActivitySpec(
        "HttpRequest",
        "System",
        required=("url", "method"),
        property_types={"url": "string", "method": "string", "output": "variable"},
    ),
    "SendEmail": ActivitySpec(
        "SendEmail",
        "System",
        required=("to", "subject", "body"),
        property_types={"to": "string", "subject": "string", "body": "expression"},
    ),
}


def search_activities(query: str) -> list[dict[str, Any]]:
    """Return a stable, simple relevance ranking for agent discovery."""

    normalized = query.strip().lower()
    scored: list[tuple[int, ActivitySpec]] = []
    for spec in ACTIVITY_SPECS.values():
        haystack = " ".join((spec.type, spec.category, spec.description)).lower()
        if not normalized:
            score = 1
        elif normalized == spec.type.lower():
            score = 100
        elif normalized in spec.type.lower():
            score = 80
        elif normalized in haystack:
            score = 50
        else:
            terms = [term for term in normalized.split() if term]
            score = 10 if terms and any(term in haystack for term in terms) else 0
        if score:
            scored.append((score, spec))
    scored.sort(key=lambda item: (-item[0], item[1].type))
    return [
        {
            "name": spec.type,
            "category": spec.category,
            "required": list(spec.required),
            "property_types": spec.property_types,
            "container": spec.container,
            "branches": list(spec.branches),
            "description": spec.description,
        }
        for _, spec in scored
    ]
