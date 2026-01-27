"""
Workflow Manager - Manages agent workflows, handoffs, and flow control.
Supports verbal command-based agent redirection and workflow design.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    agent_name: str
    action: str  # "execute", "delegate", "wait", "condition", "loop"
    description: str
    inputs: dict = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)  # Step IDs
    conditions: dict = field(default_factory=dict)  # For conditional branching
    on_error: Optional[str] = None  # Step ID to jump to on error


@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str
    name: str
    description: str
    trigger: str  # "manual", "command", "pattern", "event"
    trigger_pattern: Optional[str] = None  # For pattern-based triggers
    steps: list[WorkflowStep] = field(default_factory=list)
    entry_point: Optional[str] = None  # First step ID
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentHandoff:
    """Represents a handoff from one agent to another."""
    from_agent: str
    to_agent: str
    context: dict
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class WorkflowManager:
    """
    Manages agent workflows, handoffs, and flow control.
    Supports verbal commands for runtime agent redirection.
    """

    # Command patterns for verbal agent control
    HANDOFF_PATTERNS = [
        (r"hand\s*off\s+to\s+(\S+)", "handoff"),
        (r"switch\s+to\s+(\S+)", "switch"),
        (r"delegate\s+to\s+(\S+)", "delegate"),
        (r"use\s+(\S+)\s+agent", "use"),
        (r"let\s+(\S+)\s+handle", "delegate"),
        (r"pass\s+to\s+(\S+)", "handoff"),
        (r"transfer\s+to\s+(\S+)", "transfer"),
        (r"continue\s+with\s+(\S+)", "continue"),
    ]

    FLOW_PATTERNS = [
        (r"pause\s+workflow", "pause"),
        (r"resume\s+workflow", "resume"),
        (r"cancel\s+workflow", "cancel"),
        (r"restart\s+workflow", "restart"),
        (r"skip\s+to\s+(\S+)", "skip"),
        (r"go\s+back\s+to\s+(\S+)", "goback"),
        (r"retry\s+(?:last\s+)?step", "retry"),
    ]

    def __init__(self, config_dir: Optional[Path] = None):
        self.home = Path.home()
        self.config_dir = config_dir or (self.home / ".claude" / "workflows")
        self.workflows: dict[str, Workflow] = {}
        self.active_workflow: Optional[str] = None
        self.current_step: Optional[str] = None
        self.handoff_history: list[AgentHandoff] = []
        self._load_workflows()

    def _load_workflows(self) -> None:
        """Load all workflow definitions."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_workflows()
            return

        for wf_file in self.config_dir.glob("*.json"):
            try:
                data = json.loads(wf_file.read_text())
                workflow = self._parse_workflow(data)
                self.workflows[workflow.id] = workflow
            except Exception:
                continue

    def _create_default_workflows(self) -> None:
        """Create some default workflow templates."""
        # Code review workflow
        review_wf = Workflow(
            id="code-review",
            name="Code Review Workflow",
            description="Comprehensive code review with multiple specialist agents",
            trigger="command",
            trigger_pattern="/review",
            steps=[
                WorkflowStep(
                    id="analyze",
                    agent_name="code-explorer",
                    action="execute",
                    description="Analyze codebase and identify areas for review",
                    next_steps=["security", "quality"],
                ),
                WorkflowStep(
                    id="security",
                    agent_name="security-reviewer",
                    action="execute",
                    description="Check for security vulnerabilities",
                    next_steps=["summarize"],
                ),
                WorkflowStep(
                    id="quality",
                    agent_name="quality-reviewer",
                    action="execute",
                    description="Review code quality and best practices",
                    next_steps=["summarize"],
                ),
                WorkflowStep(
                    id="summarize",
                    agent_name="master-developer",
                    action="execute",
                    description="Compile findings and generate report",
                    next_steps=[],
                ),
            ],
            entry_point="analyze",
        )
        self.workflows["code-review"] = review_wf
        self._save_workflow(review_wf)

        # Feature development workflow
        feature_wf = Workflow(
            id="feature-dev",
            name="Feature Development Workflow",
            description="Guided feature implementation with planning and testing",
            trigger="command",
            trigger_pattern="/feature",
            steps=[
                WorkflowStep(
                    id="plan",
                    agent_name="project-planner",
                    action="execute",
                    description="Create implementation plan",
                    next_steps=["implement"],
                ),
                WorkflowStep(
                    id="implement",
                    agent_name="master-developer",
                    action="delegate",
                    description="Implement the feature",
                    next_steps=["test"],
                ),
                WorkflowStep(
                    id="test",
                    agent_name="test-engineer",
                    action="execute",
                    description="Write and run tests",
                    next_steps=["review"],
                ),
                WorkflowStep(
                    id="review",
                    agent_name="code-reviewer",
                    action="execute",
                    description="Review implementation",
                    next_steps=[],
                ),
            ],
            entry_point="plan",
        )
        self.workflows["feature-dev"] = feature_wf
        self._save_workflow(feature_wf)

    def _parse_workflow(self, data: dict) -> Workflow:
        """Parse workflow from dictionary."""
        steps = [
            WorkflowStep(
                id=s.get("id", ""),
                agent_name=s.get("agent_name", ""),
                action=s.get("action", "execute"),
                description=s.get("description", ""),
                inputs=s.get("inputs", {}),
                outputs=s.get("outputs", []),
                next_steps=s.get("next_steps", []),
                conditions=s.get("conditions", {}),
                on_error=s.get("on_error"),
            )
            for s in data.get("steps", [])
        ]

        return Workflow(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            trigger=data.get("trigger", "manual"),
            trigger_pattern=data.get("trigger_pattern"),
            steps=steps,
            entry_point=data.get("entry_point"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def _save_workflow(self, workflow: Workflow) -> None:
        """Save a workflow to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        wf_file = self.config_dir / f"{workflow.id}.json"

        data = {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "trigger": workflow.trigger,
            "trigger_pattern": workflow.trigger_pattern,
            "steps": [
                {
                    "id": s.id,
                    "agent_name": s.agent_name,
                    "action": s.action,
                    "description": s.description,
                    "inputs": s.inputs,
                    "outputs": s.outputs,
                    "next_steps": s.next_steps,
                    "conditions": s.conditions,
                    "on_error": s.on_error,
                }
                for s in workflow.steps
            ],
            "entry_point": workflow.entry_point,
            "metadata": workflow.metadata,
            "created_at": workflow.created_at,
            "updated_at": datetime.now().isoformat(),
        }

        wf_file.write_text(json.dumps(data, indent=2))

    def parse_verbal_command(self, text: str) -> Optional[dict]:
        """
        Parse verbal commands for agent handoffs and flow control.

        Returns dict with:
            - type: "handoff", "flow", or None
            - action: specific action
            - target: target agent or step (if applicable)
        """
        text_lower = text.lower().strip()

        # Check handoff patterns
        for pattern, action in self.HANDOFF_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                return {
                    "type": "handoff",
                    "action": action,
                    "target": match.group(1),
                    "original": text,
                }

        # Check flow control patterns
        for pattern, action in self.FLOW_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                result = {
                    "type": "flow",
                    "action": action,
                    "original": text,
                }
                if match.groups():
                    result["target"] = match.group(1)
                return result

        return None

    def execute_handoff(self, from_agent: str, to_agent: str, context: dict,
                        reason: str = "User requested") -> AgentHandoff:
        """Execute a handoff from one agent to another."""
        handoff = AgentHandoff(
            from_agent=from_agent,
            to_agent=to_agent,
            context=context,
            reason=reason,
        )
        self.handoff_history.append(handoff)

        # Keep only last 50 handoffs
        if len(self.handoff_history) > 50:
            self.handoff_history = self.handoff_history[-50:]

        return handoff

    def create_workflow(self, name: str, description: str,
                        trigger: str = "manual") -> Workflow:
        """Create a new workflow."""
        wf_id = name.lower().replace(" ", "-").replace("_", "-")
        wf_id = re.sub(r'[^a-z0-9-]', '', wf_id)

        workflow = Workflow(
            id=wf_id,
            name=name,
            description=description,
            trigger=trigger,
        )

        self.workflows[wf_id] = workflow
        self._save_workflow(workflow)
        return workflow

    def add_step(self, workflow_id: str, agent_name: str, action: str,
                 description: str, **kwargs) -> Optional[WorkflowStep]:
        """Add a step to a workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        step_id = f"step-{len(workflow.steps) + 1}"

        step = WorkflowStep(
            id=step_id,
            agent_name=agent_name,
            action=action,
            description=description,
            inputs=kwargs.get("inputs", {}),
            outputs=kwargs.get("outputs", []),
            next_steps=kwargs.get("next_steps", []),
            conditions=kwargs.get("conditions", {}),
            on_error=kwargs.get("on_error"),
        )

        workflow.steps.append(step)

        # Set as entry point if first step
        if len(workflow.steps) == 1:
            workflow.entry_point = step_id

        self._save_workflow(workflow)
        return step

    def connect_steps(self, workflow_id: str, from_step: str, to_step: str,
                      condition: Optional[dict] = None) -> bool:
        """Connect two steps in a workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return False

        # Find the from step
        for step in workflow.steps:
            if step.id == from_step:
                if to_step not in step.next_steps:
                    step.next_steps.append(to_step)
                if condition:
                    step.conditions[to_step] = condition
                self._save_workflow(workflow)
                return True

        return False

    def start_workflow(self, workflow_id: str) -> Optional[WorkflowStep]:
        """Start executing a workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow or not workflow.entry_point:
            return None

        self.active_workflow = workflow_id
        self.current_step = workflow.entry_point

        # Find and return the entry step
        for step in workflow.steps:
            if step.id == workflow.entry_point:
                return step

        return None

    def get_next_steps(self, workflow_id: str, current_step: str,
                       context: dict) -> list[WorkflowStep]:
        """Get possible next steps based on current state and conditions."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return []

        # Find current step
        current = None
        for step in workflow.steps:
            if step.id == current_step:
                current = step
                break

        if not current:
            return []

        # Get next steps, evaluating conditions if present
        next_steps = []
        for next_id in current.next_steps:
            for step in workflow.steps:
                if step.id == next_id:
                    # Check condition if exists
                    condition = current.conditions.get(next_id, {})
                    if not condition or self._evaluate_condition(condition, context):
                        next_steps.append(step)
                    break

        return next_steps

    def _evaluate_condition(self, condition: dict, context: dict) -> bool:
        """Evaluate a condition against the current context."""
        # Simple condition evaluation
        op = condition.get("op", "eq")
        field = condition.get("field", "")
        value = condition.get("value")

        actual = context.get(field)

        if op == "eq":
            return actual == value
        elif op == "ne":
            return actual != value
        elif op == "contains":
            return value in str(actual) if actual else False
        elif op == "exists":
            return field in context
        elif op == "true":
            return bool(actual)
        elif op == "false":
            return not bool(actual)

        return True

    def list_workflows(self) -> list[Workflow]:
        """Get all workflows."""
        return list(self.workflows.values())

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a specific workflow."""
        return self.workflows.get(workflow_id)

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id not in self.workflows:
            return False

        del self.workflows[workflow_id]

        wf_file = self.config_dir / f"{workflow_id}.json"
        if wf_file.exists():
            wf_file.unlink()

        return True

    def to_ascii_diagram(self, workflow_id: str) -> str:
        """Generate ASCII diagram of a workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return "Workflow not found"

        lines = [
            f"Workflow: {workflow.name}",
            f"Trigger: {workflow.trigger}",
            "",
        ]

        # Build step map
        steps_by_id = {s.id: s for s in workflow.steps}

        # Generate diagram
        def add_step(step_id: str, indent: int = 0, visited: set = None):
            if visited is None:
                visited = set()

            if step_id in visited:
                lines.append("  " * indent + f"[-> {step_id} (loop)]")
                return

            visited.add(step_id)
            step = steps_by_id.get(step_id)
            if not step:
                return

            prefix = "  " * indent
            lines.append(f"{prefix}+-- [{step.agent_name}]")
            lines.append(f"{prefix}|   {step.description}")

            for next_id in step.next_steps:
                lines.append(f"{prefix}|")
                add_step(next_id, indent + 1, visited.copy())

        if workflow.entry_point:
            add_step(workflow.entry_point)
        else:
            for step in workflow.steps:
                add_step(step.id)

        return "\n".join(lines)

    def get_handoff_history(self, limit: int = 10) -> list[AgentHandoff]:
        """Get recent handoff history."""
        return self.handoff_history[-limit:]

    def suggest_next_agent(self, current_agent: str, task_description: str) -> list[str]:
        """Suggest next agents based on task description."""
        suggestions = []

        # Simple keyword-based suggestions
        keywords = {
            "test": ["test-engineer", "quality-reviewer"],
            "security": ["security-reviewer"],
            "python": ["python-dev"],
            "typescript": ["typescript-dev"],
            "frontend": ["typescript-dev", "frontend-design"],
            "database": ["db-engineer"],
            "deploy": ["devops-engineer", "infra-engineer"],
            "review": ["code-reviewer", "quality-reviewer"],
            "plan": ["project-planner", "task-decomposer"],
            "document": ["doc-curator"],
        }

        task_lower = task_description.lower()
        for keyword, agents in keywords.items():
            if keyword in task_lower:
                for agent in agents:
                    if agent != current_agent and agent not in suggestions:
                        suggestions.append(agent)

        return suggestions[:5]
