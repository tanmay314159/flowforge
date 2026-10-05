import json
import tempfile
import unittest
from pathlib import Path

from flowforge import WorkflowBuilder
from flowforge.model import WorkflowError


class BuilderTests(unittest.TestCase):
    def test_nested_if_and_round_trip(self) -> None:
        builder = WorkflowBuilder.create_project("Nested")
        builder.create_variable("name", "String")
        condition = builder.add_activity("If", {"condition": "{{name}} != ''"})
        then_id = builder.add_activity(
            "Assign", {"variable": "name", "value": '"Ada"'}, parent_id=condition, branch="then"
        )
        else_id = builder.add_activity(
            "Assign", {"variable": "name", "value": '"Unknown"'}, parent_id=condition, branch="else"
        )

        self.assertEqual(then_id, "activity-2")
        self.assertEqual(else_id, "activity-3")
        self.assertEqual(builder.project.find(condition).branches.keys(), {"then", "else"})

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.json"
            builder.save(path)
            loaded = WorkflowBuilder.load(path)
            self.assertEqual(loaded.project.to_dict(), builder.project.to_dict())

    def test_duplicate_names_and_invalid_parent_are_rejected(self) -> None:
        builder = WorkflowBuilder.create_project("Errors")
        builder.create_variable("value", "String")
        with self.assertRaises(WorkflowError):
            builder.create_variable("value", "String")
        with self.assertRaises(WorkflowError):
            builder.add_activity("Click", {"target": "x"}, parent_id="missing")

    def test_json_is_valid(self) -> None:
        builder = WorkflowBuilder.create_project("JSON")
        self.assertEqual(json.loads(json.dumps(builder.project.to_dict()))["name"], "JSON")
