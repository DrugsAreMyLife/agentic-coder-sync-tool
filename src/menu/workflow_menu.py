"""Workflow Menu for designing and managing agent workflows."""

import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu
from utils.workflow_manager import WorkflowManager


class WorkflowMenu(BaseMenu):
    """Interactive menu for workflow design and agent handoffs."""

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer
        self.manager = WorkflowManager()

    def run(self) -> Optional[str]:
        """Run the workflow menu loop."""
        while True:
            self.clear_screen()
            self._draw_menu()

            choice = self.prompt()

            if choice.lower() == 'q':
                return None
            elif choice == '1':
                self._list_workflows()
            elif choice == '2':
                self._create_workflow()
            elif choice == '3':
                self._view_workflow()
            elif choice == '4':
                self._handoff_history()
            elif choice == '5':
                self._verbal_commands()
            elif choice == '6':
                self._edit_workflow()

    def _draw_menu(self) -> None:
        """Draw the workflow menu."""
        c = self.colors

        self.draw_box("WORKFLOW DESIGNER")

        workflows = self.manager.list_workflows()
        print(f"  Workflows defined: {len(workflows)}")
        print(f"  Active: {self.manager.active_workflow or 'None'}")
        print()

        self.draw_option("1", "List Workflows", "View all workflow definitions")
        print()
        self.draw_option("2", "Create Workflow", "Design a new agent workflow")
        print()
        self.draw_option("3", "View Workflow", "See workflow diagram")
        print()
        self.draw_option("4", "Handoff History", "View agent handoff log")
        print()
        self.draw_option("5", "Verbal Commands", "Learn handoff commands")
        print()
        self.draw_option("6", "Edit Workflow", "Modify existing workflow")
        print()
        self.draw_option("q", "Back")

    def _list_workflows(self) -> None:
        """List all defined workflows."""
        self.clear_screen()
        self.draw_box("WORKFLOWS")

        c = self.colors
        workflows = self.manager.list_workflows()

        if not workflows:
            print(f"  {c.colorize('No workflows defined', c.DIM)}")
            print()
            print("  Create a workflow to orchestrate multiple agents")
            print("  working together on complex tasks.")
        else:
            print(f"  {'#':<4} {'Name':<25} {'Trigger':<12} {'Steps'}")
            print(f"  {'-' * 55}")

            for i, wf in enumerate(workflows, 1):
                step_count = len(wf.steps)
                print(f"  [{i}] {wf.name:<25} {wf.trigger:<12} {step_count} steps")
                if wf.description:
                    print(f"      {c.colorize(wf.description[:50], c.DIM)}")

        self.wait_for_key()

    def _create_workflow(self) -> None:
        """Create a new workflow interactively."""
        self.clear_screen()
        self.draw_box("CREATE WORKFLOW", "1/3")

        name = self.prompt_text("Workflow name")
        if not name:
            return

        description = self.prompt_text("Description")

        self.clear_screen()
        self.draw_box("CREATE WORKFLOW", "2/3")

        print("  Select trigger type:")
        print("  [1] manual   - Started by user command")
        print("  [2] command  - Triggered by /slash command")
        print("  [3] pattern  - Triggered by text pattern")

        trigger_choice = self.prompt()
        trigger_map = {"1": "manual", "2": "command", "3": "pattern"}
        trigger = trigger_map.get(trigger_choice, "manual")

        trigger_pattern = None
        if trigger in ("command", "pattern"):
            trigger_pattern = self.prompt_text("Trigger pattern (e.g., /review or 'help me with')")

        # Create the workflow
        workflow = self.manager.create_workflow(name, description, trigger)
        if trigger_pattern:
            workflow.trigger_pattern = trigger_pattern
            self.manager._save_workflow(workflow)

        self.clear_screen()
        self.draw_box("CREATE WORKFLOW", "3/3")

        self.print_success(f"Created workflow: {workflow.id}")
        print()

        # Add steps
        if self.prompt_confirm("Add steps now?"):
            self._add_steps_to_workflow(workflow.id)

        self.wait_for_key()

    def _add_steps_to_workflow(self, workflow_id: str) -> None:
        """Add steps to a workflow."""
        c = self.colors
        agents = [a.name for a in self.syncer.agents]

        while True:
            self.clear_screen()
            self.draw_box(f"ADD STEP TO: {workflow_id}")

            workflow = self.manager.get_workflow(workflow_id)
            if workflow and workflow.steps:
                print("  Current steps:")
                for step in workflow.steps:
                    print(f"    - {step.id}: [{step.agent_name}] {step.description[:30]}")
                print()

            # Select agent
            print("  Available agents:")
            for i, agent in enumerate(agents[:15], 1):
                print(f"    [{i}] {agent}")
            if len(agents) > 15:
                print(f"    ... and {len(agents) - 15} more")

            print()
            agent_choice = self.prompt("Select agent (or 'q' to finish)")

            if agent_choice.lower() == 'q':
                break

            try:
                idx = int(agent_choice) - 1
                if 0 <= idx < len(agents):
                    agent_name = agents[idx]
                else:
                    continue
            except ValueError:
                # Try as agent name
                if agent_choice in agents:
                    agent_name = agent_choice
                else:
                    continue

            # Get step details
            description = self.prompt_text("Step description")

            print()
            print("  Action type:")
            print("  [1] execute  - Agent performs work")
            print("  [2] delegate - Agent spawns sub-agents")
            print("  [3] wait     - Wait for condition")

            action_choice = self.prompt()
            action_map = {"1": "execute", "2": "delegate", "3": "wait"}
            action = action_map.get(action_choice, "execute")

            # Add the step
            step = self.manager.add_step(
                workflow_id,
                agent_name,
                action,
                description or f"{agent_name} step",
            )

            if step:
                self.print_success(f"Added step: {step.id}")

                # Connect to previous step if exists
                if workflow.steps and len(workflow.steps) > 1:
                    prev_step = workflow.steps[-2]
                    if self.prompt_confirm(f"Connect from '{prev_step.id}'?"):
                        self.manager.connect_steps(workflow_id, prev_step.id, step.id)

    def _view_workflow(self) -> None:
        """View a workflow diagram."""
        self.clear_screen()
        self.draw_box("VIEW WORKFLOW")

        workflows = self.manager.list_workflows()

        if not workflows:
            print("  No workflows to view")
            self.wait_for_key()
            return

        c = self.colors

        for i, wf in enumerate(workflows, 1):
            print(f"  [{i}] {wf.name}")

        print()
        choice = self.prompt("Select workflow")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(workflows):
                wf = workflows[idx]

                self.clear_screen()
                self.draw_box(f"WORKFLOW: {wf.name}")

                diagram = self.manager.to_ascii_diagram(wf.id)
                print(diagram)
        except ValueError:
            pass

        self.wait_for_key()

    def _handoff_history(self) -> None:
        """View agent handoff history."""
        self.clear_screen()
        self.draw_box("HANDOFF HISTORY")

        c = self.colors
        history = self.manager.get_handoff_history(20)

        if not history:
            print(f"  {c.colorize('No handoffs recorded', c.DIM)}")
            print()
            print("  Handoffs occur when agents transfer work")
            print("  to other agents during workflow execution.")
        else:
            print(f"  {'Time':<20} {'From':<20} {'To':<20}")
            print(f"  {'-' * 60}")

            for handoff in reversed(history):
                time_str = handoff.timestamp[11:19] if len(handoff.timestamp) > 19 else handoff.timestamp
                print(f"  {time_str:<20} {handoff.from_agent:<20} {handoff.to_agent:<20}")
                if handoff.reason:
                    print(f"    {c.colorize(handoff.reason, c.DIM)}")

        self.wait_for_key()

    def _verbal_commands(self) -> None:
        """Show verbal command reference."""
        self.clear_screen()
        self.draw_box("VERBAL COMMANDS")

        c = self.colors

        self.draw_section("Agent Handoff Commands:")
        print("  Use these phrases to redirect work to another agent:")
        print()
        commands = [
            ("hand off to <agent>", "Transfer current task to agent"),
            ("switch to <agent>", "Change active agent"),
            ("delegate to <agent>", "Have agent take over"),
            ("use <agent> agent", "Activate specific agent"),
            ("let <agent> handle", "Pass task to agent"),
            ("pass to <agent>", "Transfer to agent"),
        ]
        for cmd, desc in commands:
            print(f"  {c.colorize(cmd, c.CYAN)}")
            print(f"    {c.colorize(desc, c.DIM)}")
            print()

        self.draw_section("Flow Control Commands:")
        flow_commands = [
            ("pause workflow", "Temporarily stop workflow"),
            ("resume workflow", "Continue paused workflow"),
            ("cancel workflow", "Stop and discard workflow"),
            ("restart workflow", "Start workflow from beginning"),
            ("skip to <step>", "Jump to specific step"),
            ("retry step", "Re-execute last step"),
        ]
        for cmd, desc in flow_commands:
            print(f"  {c.colorize(cmd, c.CYAN)}")
            print(f"    {c.colorize(desc, c.DIM)}")
            print()

        self.draw_section("Examples:")
        examples = [
            '"Hand off to test-engineer to run the tests"',
            '"Let security-reviewer check this code"',
            '"Switch to python-dev for the backend work"',
        ]
        for ex in examples:
            print(f"  {c.colorize(ex, c.GREEN)}")

        self.wait_for_key()

    def _edit_workflow(self) -> None:
        """Edit an existing workflow."""
        self.clear_screen()
        self.draw_box("EDIT WORKFLOW")

        workflows = self.manager.list_workflows()

        if not workflows:
            print("  No workflows to edit")
            self.wait_for_key()
            return

        for i, wf in enumerate(workflows, 1):
            print(f"  [{i}] {wf.name}")

        print()
        choice = self.prompt("Select workflow")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(workflows):
                wf = workflows[idx]
                self._edit_workflow_detail(wf.id)
        except ValueError:
            pass

    def _edit_workflow_detail(self, workflow_id: str) -> None:
        """Edit workflow details."""
        while True:
            self.clear_screen()

            workflow = self.manager.get_workflow(workflow_id)
            if not workflow:
                return

            self.draw_box(f"EDIT: {workflow.name}")

            print(f"  Description: {workflow.description}")
            print(f"  Trigger: {workflow.trigger}")
            print(f"  Steps: {len(workflow.steps)}")
            print()

            print("  [1] Add step")
            print("  [2] Remove step")
            print("  [3] Edit description")
            print("  [4] Delete workflow")
            print("  [q] Back")

            choice = self.prompt()

            if choice.lower() == 'q':
                return
            elif choice == '1':
                self._add_steps_to_workflow(workflow_id)
            elif choice == '2':
                self._remove_step(workflow_id)
            elif choice == '3':
                new_desc = self.prompt_text("New description", workflow.description)
                workflow.description = new_desc
                self.manager._save_workflow(workflow)
                self.print_success("Updated")
            elif choice == '4':
                if self.prompt_confirm("Delete this workflow?", default=False):
                    self.manager.delete_workflow(workflow_id)
                    self.print_success("Deleted")
                    return

    def _remove_step(self, workflow_id: str) -> None:
        """Remove a step from a workflow."""
        workflow = self.manager.get_workflow(workflow_id)
        if not workflow or not workflow.steps:
            self.print_info("No steps to remove")
            self.wait_for_key()
            return

        c = self.colors

        for i, step in enumerate(workflow.steps, 1):
            print(f"  [{i}] {step.id}: [{step.agent_name}] {step.description[:30]}")

        choice = self.prompt("Select step to remove")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(workflow.steps):
                step = workflow.steps.pop(idx)
                self.manager._save_workflow(workflow)
                self.print_success(f"Removed step: {step.id}")
        except ValueError:
            pass

        self.wait_for_key()
