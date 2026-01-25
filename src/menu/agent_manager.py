"""Agent Manager with relationship visualization and suggestions."""

from pathlib import Path
from typing import Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu
from utils.relationships import RelationshipAnalyzer
from utils.suggestions import SuggestionEngine
from utils.formatters import format_description, format_tools_list, format_model


class AgentManager(BaseMenu):
    """Interactive agent browser with hierarchy visualization."""

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer
        self.agents = syncer.agents
        self.analyzer = RelationshipAnalyzer(self.agents)
        self.suggestion_engine = SuggestionEngine()
        self.page_size = 10
        self.current_page = 0
        self.search_query = ""
        self.view_mode = "grouped"  # grouped, all, search

    def run(self) -> Optional[str]:
        """Run the agent manager loop."""
        while True:
            self.clear_screen()

            if self.view_mode == "search" and self.search_query:
                self._draw_search_results()
            elif self.view_mode == "grouped":
                self._draw_grouped_list()
            else:
                self._draw_all_list()

            choice = self.prompt()

            if choice.lower() == 'q':
                return None
            elif choice.lower() == 's':
                self._do_search()
            elif choice.lower() == 'a':
                self.view_mode = "all" if self.view_mode != "all" else "grouped"
            elif choice.lower() == 'n':
                self._create_agent()
            elif choice.lower() == 'g':
                self.view_mode = "grouped"
                self.search_query = ""
            elif choice.isdigit():
                idx = int(choice)
                agent = self._get_agent_by_index(idx)
                if agent:
                    self._show_agent_detail(agent)

    def _draw_grouped_list(self) -> None:
        """Draw agents grouped by depth/hierarchy."""
        c = self.colors
        total = len(self.agents)

        self.draw_box("AGENT MANAGER", f"{total} agents loaded")

        by_depth = self.analyzer.get_agents_by_depth()
        idx = 1

        for depth in sorted(by_depth.keys()):
            agents = by_depth[depth]
            label = self.analyzer.get_depth_label(depth)

            self.draw_section(f"{label} (depth {depth}):")

            for name in agents[:5]:  # Show up to 5 per group
                agent = self.syncer.agents[0] if not any(a.name == name for a in self.syncer.agents) else next(a for a in self.syncer.agents if a.name == name)
                if agent:
                    desc = format_description(agent.description, 35)
                    print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {name:<28} {c.colorize(desc, c.DIM)}")
                    idx += 1

            if len(agents) > 5:
                remaining = len(agents) - 5
                print(f"      {c.colorize(f'... and {remaining} more', c.DIM)}")

        print()
        print(f"  {c.colorize('[a] Show all', c.DIM)}  {c.colorize('[s] Search', c.DIM)}  {c.colorize('[n] New agent', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _draw_all_list(self) -> None:
        """Draw all agents in a flat list."""
        c = self.colors
        total = len(self.agents)

        self.draw_box("AGENT MANAGER", f"{total} agents")

        sorted_agents = sorted(self.agents, key=lambda a: a.name)

        start = self.current_page * self.page_size
        end = start + self.page_size
        page_agents = sorted_agents[start:end]

        for idx, agent in enumerate(page_agents, start=start + 1):
            desc = format_description(agent.description, 35)
            print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {agent.name:<28} {c.colorize(desc, c.DIM)}")

        # Pagination
        total_pages = (total + self.page_size - 1) // self.page_size
        current = self.current_page + 1
        print()
        print(f"  Page {current}/{total_pages}")
        print(f"  {c.colorize('[g] Grouped', c.DIM)}  {c.colorize('[s] Search', c.DIM)}  {c.colorize('[n] New agent', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _draw_search_results(self) -> None:
        """Draw search results."""
        c = self.colors

        matching = [a for a in self.agents if self.search_query.lower() in a.name.lower()
                    or self.search_query.lower() in str(a.description).lower()]

        self.draw_box("SEARCH RESULTS", f"'{self.search_query}'")

        if not matching:
            print(f"  {c.colorize('No agents found.', c.DIM)}")
        else:
            for idx, agent in enumerate(matching[:15], 1):
                desc = format_description(agent.description, 35)
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {agent.name:<28} {c.colorize(desc, c.DIM)}")

        print()
        print(f"  {c.colorize('[g] Grouped view', c.DIM)}  {c.colorize('[s] New search', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _do_search(self) -> None:
        """Prompt for search query."""
        query = self.prompt_text("Search agents")
        if query:
            self.search_query = query
            self.view_mode = "search"

    def _get_agent_by_index(self, idx: int):
        """Get agent by display index based on current view."""
        if self.view_mode == "grouped":
            all_agents = []
            by_depth = self.analyzer.get_agents_by_depth()
            for depth in sorted(by_depth.keys()):
                for name in by_depth[depth][:5]:
                    agent = next((a for a in self.agents if a.name == name), None)
                    if agent:
                        all_agents.append(agent)
            if 1 <= idx <= len(all_agents):
                return all_agents[idx - 1]
        elif self.view_mode == "search":
            matching = [a for a in self.agents if self.search_query.lower() in a.name.lower()
                        or self.search_query.lower() in str(a.description).lower()]
            if 1 <= idx <= len(matching):
                return matching[idx - 1]
        else:
            sorted_agents = sorted(self.agents, key=lambda a: a.name)
            start = self.current_page * self.page_size
            if 1 <= idx <= len(sorted_agents):
                return sorted_agents[idx - 1]
        return None

    def _show_agent_detail(self, agent) -> None:
        """Show detailed view of an agent."""
        while True:
            self.clear_screen()
            c = self.colors

            self.draw_box(f"AGENT: {agent.name}")

            # Purpose
            self.draw_section("PURPOSE")
            desc = format_description(agent.description, 200)
            print(f"  {desc}")

            # Hierarchy
            self.draw_section("HIERARCHY")
            node = self.analyzer.get_node(agent.name)
            if node:
                depth_label = self.analyzer.get_depth_label(node.depth)
                can_spawn = "can spawn agents" if node.can_spawn else "leaf node - cannot spawn"
                print(f"  Depth: {node.depth} ({depth_label}) - {can_spawn}")

                parents = self.analyzer.find_parents(agent.name)
                if parents:
                    print(f"  Parent: {', '.join(parents[:3])}")
                else:
                    print(f"  Parent: None (root)")

                if node.children:
                    print(f"  Children: {', '.join(node.children[:5])}")
                else:
                    print(f"  Children: None")

            # Tools
            self.draw_section("AUTHORIZED TOOLS")
            tools_str = format_tools_list(agent.tools, max_display=8)
            print(f"  {tools_str}")

            # Model
            self.draw_section("MODEL")
            print(f"  {format_model(agent.model)}")

            # Suggestions
            self.draw_section("INTEGRATION SUGGESTIONS")
            suggestions = self.suggestion_engine.suggest(agent)
            if suggestions:
                lines = self.suggestion_engine.format_suggestions(suggestions)
                for line in lines[:6]:
                    print(f"  {line}")
            else:
                print(f"  {c.colorize('No suggestions available', c.DIM)}")

            print()
            print(f"  {c.colorize('[e] Edit', c.DIM)}  {c.colorize('[d] Duplicate', c.DIM)}  {c.colorize('[r] Relationships', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

            choice = self.prompt()

            if choice.lower() == 'q':
                return
            elif choice.lower() == 'r':
                self._show_relationships(agent)
            elif choice.lower() == 'e':
                self._edit_agent(agent)
            elif choice.lower() == 'd':
                self._duplicate_agent(agent)

    def _show_relationships(self, agent) -> None:
        """Show relationship graph for an agent."""
        self.clear_screen()

        self.draw_box(f"AGENT RELATIONSHIPS: {agent.name}")

        graph = self.analyzer.to_ascii_graph(agent.name)
        print(graph)

        self.wait_for_key()

    def _edit_agent(self, agent) -> None:
        """Edit an agent's properties."""
        c = self.colors
        self.clear_screen()

        self.draw_box(f"EDIT: {agent.name}")

        print(f"  {c.colorize('Edit agent in external editor?', c.YELLOW)}")
        print(f"  File: {agent.source_path}")

        if self.prompt_confirm("Open in editor"):
            import subprocess
            editor = "code" if Path("/usr/local/bin/code").exists() else "nano"
            subprocess.run([editor, str(agent.source_path)], check=False)
            self.print_success("Editor opened")
        else:
            self.print_info("Edit cancelled")

        self.wait_for_key()

    def _duplicate_agent(self, agent) -> None:
        """Duplicate an agent with a new name."""
        c = self.colors

        new_name = self.prompt_text("New agent name", f"{agent.name}-copy")
        if not new_name or new_name == agent.name:
            self.print_error("Invalid name")
            self.wait_for_key()
            return

        # Create new agent file
        new_path = agent.source_path.parent / f"{new_name}.md"
        if new_path.exists():
            self.print_error(f"Agent '{new_name}' already exists")
            self.wait_for_key()
            return

        # Read original and update name
        content = agent.source_path.read_text()
        content = content.replace(f'name: {agent.name}', f'name: {new_name}', 1)

        new_path.write_text(content)
        self.print_success(f"Created {new_path}")

        # Reload agents
        self.syncer.agents = self.syncer.load_claude_agents()
        self.agents = self.syncer.agents
        self.analyzer = RelationshipAnalyzer(self.agents)

        self.wait_for_key()

    def _create_agent(self) -> None:
        """Create a new agent interactively."""
        c = self.colors
        self.clear_screen()

        self.draw_box("NEW AGENT WIZARD", "1/4")

        name = self.prompt_text("Agent name (lowercase, hyphens)")
        if not name:
            return

        description = self.prompt_text("Description")
        if not description:
            description = f"Agent for {name.replace('-', ' ')} tasks"

        self.clear_screen()
        self.draw_box("NEW AGENT WIZARD", "2/4")

        print("  Select tools (comma-separated, or * for all):")
        print()
        common_tools = ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task"]
        for i, tool in enumerate(common_tools, 1):
            print(f"  [{i}] {tool}")
        print(f"  [a] All tools (*)")

        tool_choice = self.prompt()
        if tool_choice.lower() == 'a':
            tools = ["*"]
        else:
            try:
                indices = [int(x.strip()) - 1 for x in tool_choice.split(',')]
                tools = [common_tools[i] for i in indices if 0 <= i < len(common_tools)]
            except:
                tools = ["Read", "Grep"]

        self.clear_screen()
        self.draw_box("NEW AGENT WIZARD", "3/4")

        print("  Select model:")
        print("  [1] haiku (fast, cost-effective) - Recommended")
        print("  [2] sonnet (balanced)")
        print("  [3] opus (most capable)")

        model_choice = self.prompt()
        model_map = {"1": "haiku", "2": "sonnet", "3": "opus"}
        model = model_map.get(model_choice, "haiku")

        # Create the agent file
        agents_dir = self.syncer.claude_agents
        agents_dir.mkdir(parents=True, exist_ok=True)

        agent_path = agents_dir / f"{name}.md"
        if agent_path.exists():
            self.print_error(f"Agent '{name}' already exists")
            self.wait_for_key()
            return

        tools_str = ", ".join(tools)
        content = f"""---
name: {name}
description: "{description}"
tools: [{tools_str}]
model: {model}
color: "#6366f1"
---

# {name.replace('-', ' ').title()}

{description}

## Responsibilities

- [Add responsibilities here]

## Guidelines

- [Add guidelines here]
"""

        agent_path.write_text(content)

        self.clear_screen()
        self.draw_box("NEW AGENT WIZARD", "4/4")

        self.print_success(f"Created {agent_path}")

        # Reload agents
        self.syncer.agents = self.syncer.load_claude_agents()
        self.agents = self.syncer.agents
        self.analyzer = RelationshipAnalyzer(self.agents)

        self.wait_for_key()
