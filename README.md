# FlowForge AI

FlowForge is an agent-first workflow construction layer for a bounded subset
of UiPath activities. Agents work with typed operations and a hierarchical
intermediate representation instead of directly writing XAML.

This repository contains the first MVP slice:

- Typed activity catalog and activity discovery
- Hierarchical workflow model with sequences and `If` branches
- Safe builder operations for activities, variables, arguments, and edges
- Machine-readable static validation with repair suggestions
- Deterministic FlowForge JSON persistence
- A UiPath-shaped XAML draft renderer
- A dependency-free CLI and stdio MCP server

## Quick start

The project requires Python 3.10 or newer and has no runtime dependencies.

```bash
python -m flowforge.cli create --name FormEntry --output flowforge.json
python -m flowforge.cli search browser
python -m flowforge.cli validate flowforge.json
python -m flowforge.cli render flowforge.json --output dist
```

The renderer creates:

- `Main.xaml`
- `project.json`
- `flowforge.json`

The XAML renderer currently targets the supported MVP subset and preserves
FlowForge properties in a stable form. Exact UiPath activity serialization is
package/version-specific; a package adapter is the next step before treating
the output as a universal Studio import format.

## Building a workflow in Python

```python
from flowforge import WorkflowBuilder, validate_project

builder = WorkflowBuilder.create_project("FormEntry")
builder.create_variable("result", "String")
browser = builder.add_activity(
    "UseApplicationBrowser",
    {"url": "https://example.test"},
)
builder.add_activity(
    "TypeInto",
    {
        "target": {"selector": "<input id='name' />"},
        "text": "Ada Lovelace",
    },
    parent_id=browser,
)
builder.add_activity(
    "GetText",
    {
        "target": {"selector": "<output id='result' />"},
        "output": "result",
    },
    parent_id=browser,
)

report = validate_project(builder.project)
assert report.valid, report.to_dict()
builder.save("form-entry.json")
```

## MCP server

The server communicates over newline-delimited JSON-RPC on stdin/stdout:

```bash
python -m flowforge.cli serve
```

It exposes `create_project`, `load_project`, `search_activities`,
`add_activity`, `connect_activities`, `create_variable`, `create_argument`,
`validate_workflow`, `save_project`, and `render_project` through MCP's
`tools/list` and `tools/call` methods.

## Model decisions

The internal representation is a tree plus optional explicit connections:

- A tree models UiPath's nested activities and variable scopes better than a
  flat graph.
- Explicit connections are retained for future flowchart support.
- IDs are deterministic (`activity-1`, `activity-2`, ...), making agent
  retries and diffs easier to reason about.
- Static validation is separate from runtime/environment validation. A selector
  can be checked for shape here, but only a real target application can prove
  that it resolves.

## Development

Run the standard-library test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

The next production-hardening step is a UiPath package adapter pinned to one
known Studio/runtime version. That adapter should be tested against actual
Studio opening, validation, and execution before broadening the activity set.
