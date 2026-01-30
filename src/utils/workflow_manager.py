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
    # Visual designer fields
    position_x: int = 0  # Canvas X position
    position_y: int = 0  # Canvas Y position
    node_type: str = "agent"  # start, end, agent, conditional, loop_start, loop_end, hitl, wait, parallel, join
    parameters: dict = field(default_factory=dict)  # Node-specific configuration


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
                position_x=s.get("position_x", 0),
                position_y=s.get("position_y", 0),
                node_type=s.get("node_type", "agent"),
                parameters=s.get("parameters", {}),
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
                    "position_x": s.position_x,
                    "position_y": s.position_y,
                    "node_type": s.node_type,
                    "parameters": s.parameters,
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

        step_id = kwargs.get("id") or f"step-{len(workflow.steps) + 1}"

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
            position_x=kwargs.get("position_x", 0),
            position_y=kwargs.get("position_y", 0),
            node_type=kwargs.get("node_type", "agent"),
            parameters=kwargs.get("parameters", {}),
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

    def to_executable_prompt(self, workflow_id: str, user_prompt: str = "") -> Optional[str]:
        """
        Generate an executable prompt for Claude to execute a workflow.

        This transforms a workflow definition into structured instructions
        that can be executed by the sync-orchestrator agent.
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        # Build step descriptions in execution order
        steps_by_id = {s.id: s for s in workflow.steps}

        def get_ordered_steps() -> list[tuple[int, WorkflowStep]]:
            """Order steps by dependency (entry point first, then breadth-first)."""
            if not workflow.entry_point:
                return [(i + 1, s) for i, s in enumerate(workflow.steps)]

            ordered = []
            visited = set()
            queue = [workflow.entry_point]
            step_num = 1

            while queue:
                step_id = queue.pop(0)
                if step_id in visited:
                    continue
                visited.add(step_id)

                step = steps_by_id.get(step_id)
                if step:
                    ordered.append((step_num, step))
                    step_num += 1
                    queue.extend(step.next_steps)

            return ordered

        ordered_steps = get_ordered_steps()

        # Build the prompt
        lines = [
            f'You are executing the "{workflow.name}" workflow.',
            "",
            "## Workflow Overview",
            workflow.description,
            "",
            "## Steps to Execute",
            "",
        ]

        for num, step in ordered_steps:
            lines.append(f"### Step {num}: {step.description}")
            lines.append(f"- **Agent**: {step.agent_name}")
            lines.append(f"- **Action**: {step.action}")

            if step.inputs:
                inputs_str = ", ".join(f"{k}={v}" for k, v in step.inputs.items())
                lines.append(f"- **Inputs**: {inputs_str}")

            if step.next_steps:
                next_names = []
                for next_id in step.next_steps:
                    next_step = steps_by_id.get(next_id)
                    if next_step:
                        next_names.append(f"{next_id} ({next_step.agent_name})")
                    else:
                        next_names.append(next_id)
                lines.append(f"- **On completion, proceed to**: {', '.join(next_names)}")
            else:
                lines.append("- **On completion**: Workflow ends")

            if step.on_error:
                error_step = steps_by_id.get(step.on_error)
                error_name = f"{step.on_error} ({error_step.agent_name})" if error_step else step.on_error
                lines.append(f"- **On error**: Jump to {error_name}")

            if step.conditions:
                lines.append("- **Conditional branches**:")
                for target_id, condition in step.conditions.items():
                    cond_str = f"  - If {condition.get('field', '?')} {condition.get('op', '==')} {condition.get('value', '?')}: go to {target_id}"
                    lines.append(cond_str)

            lines.append("")

        if user_prompt:
            lines.extend([
                "## User's Request",
                user_prompt,
                "",
            ])

        lines.extend([
            "## Execution Instructions",
            "",
            "1. Start with step 1 (the entry point)",
            "2. For each step, use the Task tool to invoke the specified agent",
            "3. Pass relevant context and outputs between steps",
            "4. If a step has conditional branches, evaluate the condition and follow the appropriate path",
            "5. If a step fails and has an on_error handler, jump to that step",
            "6. Report progress after each step with [+] for success, [-] for failure",
            "7. When all steps complete, compile a final summary of results",
            "",
            "Begin execution now.",
        ])

        return "\n".join(lines)

    def to_skill_md(self, workflow_id: str) -> Optional[str]:
        """
        Generate a SKILL.md file from a workflow.

        This allows a workflow to be invoked as a skill via its trigger pattern.
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        # Generate the executable prompt as the skill content
        exec_prompt = self.to_executable_prompt(workflow_id)
        if not exec_prompt:
            return None

        lines = [
            f"# {workflow.name}",
            "",
            workflow.description,
            "",
            "## Trigger",
            "",
            f"This workflow is triggered by: `{workflow.trigger_pattern or workflow.trigger}`",
            "",
            "## Workflow Steps",
            "",
        ]

        # Add a summary of steps
        for step in workflow.steps:
            lines.append(f"- **{step.agent_name}**: {step.description}")

        lines.extend([
            "",
            "## Execution",
            "",
            "When triggered, execute the following:",
            "",
            "```",
            exec_prompt,
            "```",
        ])

        return "\n".join(lines)

    def generate_command_md(self, workflow_id: str) -> Optional[str]:
        """
        Generate a command markdown file for a workflow.

        This creates a slash command that can invoke the workflow directly.
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        # Generate the executable prompt
        exec_prompt = self.to_executable_prompt(workflow_id)
        if not exec_prompt:
            return None

        # Collect all unique agent names for Task tool delegation
        agents = set()
        for step in workflow.steps:
            if step.agent_name:
                agents.add(step.agent_name)

        # Build allowed tools list
        allowed_tools = ["Task", "Read", "Bash", "Glob", "Grep"]

        lines = [
            "---",
            f"name: {workflow_id}",
            f"description: {workflow.description or workflow.name}",
            "arguments:",
            "  - name: prompt",
            '    description: "Additional context or instructions for the workflow"',
            "    required: false",
            "allowed_tools:",
        ]

        for tool in allowed_tools:
            lines.append(f"  - {tool}")

        lines.extend([
            "---",
            "",
            f"# {workflow.name}",
            "",
            workflow.description or "",
            "",
            "## Workflow Overview",
            "",
        ])

        # Add step summary
        for i, step in enumerate(workflow.steps, 1):
            lines.append(f"{i}. **{step.agent_name or step.node_type}**: {step.description}")

        lines.extend([
            "",
            "## Execution Instructions",
            "",
            exec_prompt,
            "",
            "## User Context",
            "",
            "${ARGUMENTS.prompt}",
        ])

        return "\n".join(lines)

    def generate_prompt_md(self, workflow_id: str) -> Optional[str]:
        """
        Generate a standalone prompt markdown file for a workflow.

        This creates a portable prompt file that can be used with any LLM.
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        # Generate the executable prompt
        exec_prompt = self.to_executable_prompt(workflow_id)
        if not exec_prompt:
            return None

        lines = [
            f"# {workflow.name}",
            "",
            f"> {workflow.description}",
            "",
            "## Instructions",
            "",
            "This is a workflow prompt that can be used to guide an AI assistant through",
            "a multi-step process involving multiple specialized agents.",
            "",
            "## Workflow Definition",
            "",
            exec_prompt,
            "",
            "---",
            "",
            f"Generated from workflow: `{workflow_id}`",
            f"Source: `~/.claude/workflows/{workflow_id}.json`",
        ]

        return "\n".join(lines)

    def get_export_paths(self, workflow_id: str) -> dict:
        """
        Get paths where exports would be created for a workflow.

        Returns dict with paths for each export type.
        """
        return {
            "skill": self.home / ".claude" / "skills" / workflow_id / "SKILL.md",
            "command": self.home / ".claude" / "plugins" / "agent-sync" / "commands" / f"{workflow_id}.md",
            "prompt": self.config_dir / f"{workflow_id}.prompt.md",
        }

    def get_export_status(self, workflow_id: str) -> dict:
        """
        Check which exports exist for a workflow.

        Returns dict with boolean for each export type.
        """
        paths = self.get_export_paths(workflow_id)
        return {
            "skill": paths["skill"].exists(),
            "command": paths["command"].exists(),
            "prompt": paths["prompt"].exists(),
        }

    def export_as_skill(self, workflow_id: str) -> Optional[Path]:
        """
        Export workflow as a SKILL.md file.

        Creates ~/.claude/skills/{workflow_id}/SKILL.md
        """
        skill_md = self.to_skill_md(workflow_id)
        if not skill_md:
            return None

        paths = self.get_export_paths(workflow_id)
        skill_dir = paths["skill"].parent
        skill_dir.mkdir(parents=True, exist_ok=True)
        paths["skill"].write_text(skill_md)
        return paths["skill"]

    def export_as_command(self, workflow_id: str) -> Optional[Path]:
        """
        Export workflow as a slash command.

        Creates ~/.claude/plugins/agent-sync/commands/{workflow_id}.md
        """
        command_md = self.generate_command_md(workflow_id)
        if not command_md:
            return None

        paths = self.get_export_paths(workflow_id)
        cmd_dir = paths["command"].parent
        cmd_dir.mkdir(parents=True, exist_ok=True)
        paths["command"].write_text(command_md)
        return paths["command"]

    def export_as_prompt(self, workflow_id: str) -> Optional[Path]:
        """
        Export workflow as a standalone prompt file.

        Creates ~/.claude/workflows/{workflow_id}.prompt.md
        """
        prompt_md = self.generate_prompt_md(workflow_id)
        if not prompt_md:
            return None

        paths = self.get_export_paths(workflow_id)
        paths["prompt"].parent.mkdir(parents=True, exist_ok=True)
        paths["prompt"].write_text(prompt_md)
        return paths["prompt"]

    def delete_exports(self, workflow_id: str) -> dict:
        """
        Delete all exports for a workflow.

        Returns dict with status for each export type.
        """
        paths = self.get_export_paths(workflow_id)
        results = {}

        for export_type, path in paths.items():
            if path.exists():
                try:
                    path.unlink()
                    # Also remove skill directory if empty
                    if export_type == "skill" and path.parent.exists():
                        try:
                            path.parent.rmdir()
                        except OSError:
                            pass  # Directory not empty
                    results[export_type] = True
                except Exception:
                    results[export_type] = False
            else:
                results[export_type] = None  # Didn't exist

        return results

    def analyze_workflow_complexity(self, workflow_id: str) -> dict:
        """
        Analyze workflow complexity to determine optimal export type.

        Returns dict with:
            - complexity_score: 0-100
            - recommended_export: "command" or "skill"
            - reasons: list of factors
            - has_parallelism: bool
            - has_external_models: bool
            - step_count: int
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        reasons = []
        score = 0

        # Factor 1: Step count
        step_count = len(workflow.steps)
        if step_count <= 3:
            score += 10
            reasons.append(f"Simple workflow ({step_count} steps)")
        elif step_count <= 6:
            score += 30
            reasons.append(f"Moderate workflow ({step_count} steps)")
        else:
            score += 50
            reasons.append(f"Complex workflow ({step_count} steps)")

        # Factor 2: Parallelism
        has_parallel = any(s.node_type == "parallel" for s in workflow.steps)
        has_join = any(s.node_type == "join" for s in workflow.steps)
        has_parallelism = has_parallel or has_join
        if has_parallelism:
            score += 20
            reasons.append("Contains parallel execution branches")

        # Factor 3: External model references (check descriptions for model names)
        external_models = []
        model_keywords = ["gemini", "gpt", "codex", "openai", "anthropic", "llama", "mistral"]
        for step in workflow.steps:
            desc_lower = (step.description or "").lower()
            for model in model_keywords:
                if model in desc_lower and model not in external_models:
                    external_models.append(model)

        has_external_models = len(external_models) > 0
        if has_external_models:
            score += 15
            reasons.append(f"References external models: {', '.join(external_models)}")

        # Factor 4: Conditional logic
        has_conditionals = any(s.node_type == "conditional" for s in workflow.steps)
        if has_conditionals:
            score += 10
            reasons.append("Contains conditional branching")

        # Factor 5: HITL (Human-in-the-loop)
        has_hitl = any(s.node_type == "hitl" for s in workflow.steps)
        if has_hitl:
            score += 10
            reasons.append("Requires human approval steps")

        # Factor 6: Loops
        has_loops = any(s.node_type in ("loop_start", "loop_end") for s in workflow.steps)
        if has_loops:
            score += 10
            reasons.append("Contains iterative loops")

        # Factor 7: Trigger type
        if workflow.trigger == "pattern":
            score += 5
            reasons.append("Pattern-triggered (contextual activation)")
        elif workflow.trigger == "command":
            reasons.append("Command-triggered (direct invocation)")

        # Determine recommendation
        # Command: Simple, direct invocation, fewer steps
        # Skill: Complex orchestration, pattern matching, multi-model
        if score >= 50 or has_parallelism or has_external_models:
            recommended = "skill"
            recommendation_reason = "Complex orchestration benefits from skill's flexibility"
        elif step_count <= 4 and not has_parallelism:
            recommended = "command"
            recommendation_reason = "Simple workflow suits direct command invocation"
        else:
            recommended = "both"
            recommendation_reason = "Moderate complexity - export both for flexibility"

        return {
            "complexity_score": min(score, 100),
            "recommended_export": recommended,
            "recommendation_reason": recommendation_reason,
            "reasons": reasons,
            "has_parallelism": has_parallelism,
            "has_external_models": has_external_models,
            "external_models": external_models,
            "has_conditionals": has_conditionals,
            "has_hitl": has_hitl,
            "has_loops": has_loops,
            "step_count": step_count,
        }

    def smart_export(self, workflow_id: str) -> dict:
        """
        Intelligently export workflow based on complexity analysis.

        Automatically determines whether to export as skill, command, or both.
        Returns dict with export results and reasoning.
        """
        analysis = self.analyze_workflow_complexity(workflow_id)
        if "error" in analysis:
            return analysis

        results = {
            "analysis": analysis,
            "exports": {},
        }

        recommended = analysis["recommended_export"]

        if recommended in ("skill", "both"):
            skill_path = self.export_as_skill(workflow_id)
            results["exports"]["skill"] = str(skill_path) if skill_path else None

        if recommended in ("command", "both"):
            cmd_path = self.export_as_command(workflow_id)
            results["exports"]["command"] = str(cmd_path) if cmd_path else None

        # Always create prompt file as backup/portable option
        prompt_path = self.export_as_prompt(workflow_id)
        results["exports"]["prompt"] = str(prompt_path) if prompt_path else None

        return results

    def to_visual_format(self, workflow_id: str) -> Optional[dict]:
        """Convert workflow to visual format for the designer."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        nodes = []
        edges = []

        for step in workflow.steps:
            nodes.append({
                "id": step.id,
                "type": step.node_type,
                "x": step.position_x,
                "y": step.position_y,
                "agent": step.agent_name,
                "description": step.description,
                "action": step.action,
                "inputs": step.inputs,
                "outputs": step.outputs,
                "parameters": step.parameters,
                "on_error": step.on_error,
            })

            for next_id in step.next_steps:
                edges.append({
                    "from": step.id,
                    "to": next_id,
                    "condition": step.conditions.get(next_id),
                })

        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "trigger": workflow.trigger,
            "trigger_pattern": workflow.trigger_pattern,
            "entry_point": workflow.entry_point,
            "nodes": nodes,
            "edges": edges,
            "metadata": workflow.metadata,
        }

    def from_visual_format(self, data: dict) -> Workflow:
        """Create or update workflow from visual format."""
        wf_id = data.get("id", "")

        # Build edges map for quick lookup
        edges_map: dict[str, list] = {}
        conditions_map: dict[str, dict] = {}
        for edge in data.get("edges", []):
            from_id = edge.get("from", "")
            to_id = edge.get("to", "")
            if from_id:
                if from_id not in edges_map:
                    edges_map[from_id] = []
                edges_map[from_id].append(to_id)
                if edge.get("condition"):
                    if from_id not in conditions_map:
                        conditions_map[from_id] = {}
                    conditions_map[from_id][to_id] = edge["condition"]

        # Create steps from nodes
        steps = []
        for node in data.get("nodes", []):
            node_id = node.get("id", "")
            step = WorkflowStep(
                id=node_id,
                agent_name=node.get("agent", ""),
                action=node.get("action", "execute"),
                description=node.get("description", ""),
                inputs=node.get("inputs", {}),
                outputs=node.get("outputs", []),
                next_steps=edges_map.get(node_id, []),
                conditions=conditions_map.get(node_id, {}),
                on_error=node.get("on_error"),
                position_x=node.get("x", 0),
                position_y=node.get("y", 0),
                node_type=node.get("type", "agent"),
                parameters=node.get("parameters", {}),
            )
            steps.append(step)

        workflow = Workflow(
            id=wf_id,
            name=data.get("name", ""),
            description=data.get("description", ""),
            trigger=data.get("trigger", "manual"),
            trigger_pattern=data.get("trigger_pattern"),
            steps=steps,
            entry_point=data.get("entry_point"),
            metadata=data.get("metadata", {}),
        )

        # Save and register
        self.workflows[wf_id] = workflow
        self._save_workflow(workflow)

        return workflow

    def update_step(self, workflow_id: str, step_id: str, **kwargs) -> Optional[WorkflowStep]:
        """Update a specific step in a workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        for step in workflow.steps:
            if step.id == step_id:
                if "agent_name" in kwargs:
                    step.agent_name = kwargs["agent_name"]
                if "action" in kwargs:
                    step.action = kwargs["action"]
                if "description" in kwargs:
                    step.description = kwargs["description"]
                if "inputs" in kwargs:
                    step.inputs = kwargs["inputs"]
                if "outputs" in kwargs:
                    step.outputs = kwargs["outputs"]
                if "next_steps" in kwargs:
                    step.next_steps = kwargs["next_steps"]
                if "conditions" in kwargs:
                    step.conditions = kwargs["conditions"]
                if "on_error" in kwargs:
                    step.on_error = kwargs["on_error"]
                if "position_x" in kwargs:
                    step.position_x = kwargs["position_x"]
                if "position_y" in kwargs:
                    step.position_y = kwargs["position_y"]
                if "node_type" in kwargs:
                    step.node_type = kwargs["node_type"]
                if "parameters" in kwargs:
                    step.parameters = kwargs["parameters"]

                self._save_workflow(workflow)
                return step

        return None

    def remove_step(self, workflow_id: str, step_id: str) -> bool:
        """Remove a step from a workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return False

        # Remove the step
        workflow.steps = [s for s in workflow.steps if s.id != step_id]

        # Remove references to this step from other steps
        for step in workflow.steps:
            if step_id in step.next_steps:
                step.next_steps.remove(step_id)
            if step_id in step.conditions:
                del step.conditions[step_id]

        # Update entry point if needed
        if workflow.entry_point == step_id:
            workflow.entry_point = workflow.steps[0].id if workflow.steps else None

        self._save_workflow(workflow)
        return True
