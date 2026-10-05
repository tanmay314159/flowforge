import unittest

from flowforge import WorkflowBuilder, validate_project


class ValidatorTests(unittest.TestCase):
    def test_valid_supported_workflow(self) -> None:
        builder = WorkflowBuilder.create_project("Valid")
        builder.create_variable("output", "String")
        container = builder.add_activity("UseApplicationBrowser", {"url": "https://example.test"})
        builder.add_activity(
            "TypeInto",
            {"target": {"selector": "#name"}, "text": "Ada"},
            parent_id=container,
        )
        builder.add_activity(
            "GetText",
            {"target": {"selector": "#result"}, "output": "output"},
            parent_id=container,
        )
        report = validate_project(builder.project)
        self.assertTrue(report.valid, report.to_dict())
        self.assertEqual(report.errors, [])

    def test_missing_properties_and_variables_are_reported(self) -> None:
        builder = WorkflowBuilder.create_project("Invalid")
        builder.add_activity("TypeInto", {"target": {"selector": "#name"}, "text": "{{missing}}"})
        builder.add_activity("GetText", {"target": {"selector": ""}, "output": "unknown"})
        report = validate_project(builder.project)
        codes = {issue.code for issue in report.errors}
        self.assertIn("VARIABLE_UNDEFINED", codes)
        self.assertIn("VARIABLE_UNDEFINED", codes)
        self.assertIn("SELECTOR_EMPTY", {issue.code for issue in report.warnings})
        self.assertFalse(report.valid)

    def test_explicit_connection_cycle_is_reported(self) -> None:
        builder = WorkflowBuilder.create_project("Cycle")
        first = builder.add_activity("Assign", {"variable": "x", "value": "1"})
        second = builder.add_activity("Assign", {"variable": "x", "value": "2"})
        builder.connect_activities(first, second)
        builder.connect_activities(second, first)
        report = validate_project(builder.project)
        self.assertIn("CONNECTION_CYCLE", {issue.code for issue in report.errors})
