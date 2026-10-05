"""Command-line entry point for FlowForge."""

from __future__ import annotations

import argparse
import json
import sys

from .builder import WorkflowBuilder
from .catalog import search_activities
from .mcp import serve
from .render import render_project
from .validator import validate_project


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowforge", description="Build and validate FlowForge workflow projects.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create an empty workflow project")
    create.add_argument("--name", required=True)
    create.add_argument("--template", choices=["process", "library"], default="process")
    create.add_argument("--compatibility", default="Windows")
    create.add_argument("--output", default="flowforge.json")

    validate = subparsers.add_parser("validate", help="Validate a FlowForge JSON project")
    validate.add_argument("project")

    render = subparsers.add_parser("render", help="Render a project directory")
    render.add_argument("project")
    render.add_argument("--output", default="dist")

    search = subparsers.add_parser("search", help="Search the supported activity catalog")
    search.add_argument("query", nargs="?", default="")

    subparsers.add_parser("serve", help="Run the stdio MCP server")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "create":
        builder = WorkflowBuilder.create_project(args.name, args.template, args.compatibility)
        builder.save(args.output)
        print(f"Created {args.output}")
        return 0
    if args.command == "validate":
        report = validate_project(WorkflowBuilder.load(args.project).project)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.valid else 1
    if args.command == "render":
        builder = WorkflowBuilder.load(args.project)
        paths = render_project(builder.project, args.output)
        print(json.dumps({"files": [str(path) for path in paths]}, indent=2))
        return 0
    if args.command == "search":
        print(json.dumps({"activities": search_activities(args.query)}, indent=2, sort_keys=True))
        return 0
    if args.command == "serve":
        serve()
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
