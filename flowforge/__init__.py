"""FlowForge's dependency-light workflow construction MVP."""

from .builder import WorkflowBuilder
from .model import Argument, ActivityNode, Variable, WorkflowProject
from .validator import ValidationIssue, ValidationReport, validate_project

__all__ = [
    "ActivityNode",
    "Argument",
    "ValidationIssue",
    "ValidationReport",
    "Variable",
    "WorkflowBuilder",
    "WorkflowProject",
    "validate_project",
]

__version__ = "0.1.0"
