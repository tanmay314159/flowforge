
# FlowForge AI – Specification

## 1. Overview

FlowForge AI is a developer tool that enables AI agents (LLMs) to programmatically create, modify, validate, and deploy UiPath workflows using a structured API instead of raw XAML generation.

The system abstracts UiPath’s internal workflow format into a deterministic, tool-driven interface, allowing agents to reliably construct automation logic step-by-step.

---

## 2. Goals

### Primary Goals
- Enable AI agents to build UiPath workflows reliably
- Avoid direct generation of fragile `.xaml` files
- Provide structured primitives for workflow construction
- Support validation and self-repair loops

### Secondary Goals
- Reduce hallucination in activity usage
- Provide discoverability of UiPath activities
- Enable cross-agent compatibility via MCP

---

## 3. Non-Goals

- Replacing UiPath Studio UI
- Supporting all UiPath activities in v1
- Full visual workflow editing
- Human-first UX (this is agent-first)

---

## 4. Core Concepts

### 4.1 Workflow Model
A workflow is represented as a structured JSON graph:

- Nodes = Activities
- Edges = Execution flow
- Metadata = Variables, arguments, imports

---

### 4.2 Activity Abstraction

Each UiPath activity is exposed as:

```json
{
  "name": "Click",
  "package": "UiPath.UIAutomation.Activities",
  "inputs": {
    "target": "selector",
    "timeout": "int"
  },
  "outputs": {},
  "category": "UI"
}
```

---

### 4.3 Agent Interaction Model

Agents do NOT generate workflows directly.

They call tools like:

- create_project
- add_activity
- connect_nodes
- set_variable
- validate_workflow
- run_workflow

---

## 5. System Architecture

```
Agent (LLM)
   ↓
MCP Interface (FlowForge API)
   ↓
Workflow Builder Engine
   ↓
UiPath CLI (`uip`)
   ↓
Generated UiPath Project
   ↓
UiPath Studio / Orchestrator
```

---

## 6. MCP Tool Definitions

### 6.1 Project Management

#### create_project
Creates a new UiPath project

```json
{
  "name": "string",
  "template": "process | library"
}
```

---

#### load_project

```json
{
  "project_path": "string"
}
```

---

### 6.2 Activity Operations

#### search_activities

```json
{
  "query": "string"
}
```

Returns ranked list of relevant activities.

---

#### add_activity

```json
{
  "type": "string",
  "properties": {},
  "parent_id": "optional"
}
```

---

#### connect_activities

```json
{
  "from_id": "string",
  "to_id": "string"
}
```

---

### 6.3 Variables & Logic

#### create_variable

```json
{
  "name": "string",
  "type": "string",
  "scope": "string"
}
```

---

#### add_condition

```json
{
  "type": "If",
  "condition": "expression"
}
```

---

### 6.4 Validation & Execution

#### validate_workflow

Returns structured errors:

```json
{
  "errors": [
    {
      "activity_id": "...",
      "message": "...",
      "fix_suggestion": "..."
    }
  ]
}
```

---

#### run_workflow

```json
{
  "input_args": {}
}
```

---

#### repair_workflow

Auto-fixes common issues.

---

### 6.5 Deployment

#### publish_project

```json
{
  "environment": "string"
}
```

---

## 7. Activity Set (v1 Scope)

Support only high-value primitives:

### UI Automation
- Use Application/Browser
- Click
- Type Into
- Get Text

### Control Flow
- Sequence
- If
- For Each
- While

### Data
- Assign
- Variables
- Arguments

### Files
- Read/Write Excel
- Read Text File

### System
- HTTP Request
- Send Email

---

## 8. Validation Engine

### Responsibilities
- Check missing required inputs
- Detect invalid selectors
- Validate variable scope
- Ensure graph correctness

### Output Format
- Machine-readable errors
- Repair hints for agent loop

---

## 9. Agent Loop Pattern

Expected behavior:

1. Agent creates project
2. Adds activities step-by-step
3. Calls validate_workflow
4. Fixes issues
5. Re-validates
6. Runs workflow
7. Publishes

---

## 10. Storage

### Project Representation
- Internal: JSON graph
- Output: UiPath `.xaml` + project structure

---

## 11. CLI Integration

Use UiPath CLI (`uip`) for:

- Project scaffolding
- Packaging
- Deployment
- Running workflows

---

## 12. Extensibility

Future additions:

- Custom activity packs
- Multi-agent orchestration
- Visual editor sync
- Natural language → tool plan conversion
- Debug tracing

---

## 13. MVP Milestones

### Phase 1
- Project creation
- Add basic activities
- JSON workflow model

### Phase 2
- Validation engine
- CLI integration

### Phase 3
- Execution + repair loop

### Phase 4
- MCP packaging
- Public API

---

## 14. Success Criteria

- Agent can build a working workflow without manual edits
- ≥80% reduction in invalid workflows
- Deterministic reproducibility
- Compatible with at least 2 LLM agents

---

## 15. Example Use Case

Input:
"Download invoices from email and save to Excel"

Agent Output:
- Creates project
- Adds email reader
- Extracts attachments
- Writes to Excel
- Validates and runs successfully

---

## 16. Risks

- UiPath version compatibility
- Activity schema drift
- Over-abstraction limiting flexibility
- Agent misuse of tools

---

## 17. Future Vision

FlowForge AI becomes the standard interface layer between AI agents and RPA platforms, enabling:

- Autonomous automation creation
- Self-healing workflows
- Cross-platform automation abstraction

---