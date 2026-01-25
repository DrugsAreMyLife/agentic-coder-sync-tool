"""Agent relationship analysis for hierarchy visualization."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Import will be resolved at runtime to avoid circular imports
AgentInfo = None


def get_agent_info_class():
    """Lazy import of AgentInfo to avoid circular imports."""
    global AgentInfo
    if AgentInfo is None:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from sync_agents import AgentInfo as AI
        AgentInfo = AI
    return AgentInfo


@dataclass
class AgentNode:
    """A node in the agent relationship graph."""
    name: str
    depth: int
    parents: list[str]
    children: list[str]
    siblings: list[str]
    can_spawn: bool  # Has Task tool


class RelationshipAnalyzer:
    """
    Analyzes agent relationships based on:
    1. Explicit references in agent content
    2. Tool capabilities (Task tool = can spawn)
    3. Inferred hierarchies from naming and descriptions
    """

    # Known orchestrator/coordinator agents at root level
    ROOT_AGENTS = {
        "autonomous-orchestrator",
        "master-developer",
    }

    # Known coordinator agents (spawn others but are spawned too)
    COORDINATOR_AGENTS = {
        "task-decomposer",
        "micro-task-decomposer",
        "project-planner",
        "project-agent-setup",
        "context-consolidator",
    }

    def __init__(self, agents: list):
        self.agents = {a.name: a for a in agents}
        self.nodes: dict[str, AgentNode] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """Build the relationship graph from agent data."""
        # First pass: determine which agents can spawn (have Task tool)
        for name, agent in self.agents.items():
            can_spawn = "Task" in agent.tools or "*" in agent.tools
            self.nodes[name] = AgentNode(
                name=name,
                depth=self._calculate_depth(name, agent, can_spawn),
                parents=[],
                children=[],
                siblings=[],
                can_spawn=can_spawn,
            )

        # Second pass: find explicit references
        for name, agent in self.agents.items():
            self._parse_references(name, agent)

        # Third pass: infer siblings (same depth, similar purpose)
        self._infer_siblings()

    def _calculate_depth(self, name: str, agent, can_spawn: bool) -> int:
        """
        Calculate agent depth in hierarchy:
        0 = Root orchestrator (spawns all, spawned by none)
        1 = Coordinators (spawn specialists, spawned by root)
        2 = Mid-level (spawn leaf nodes, spawned by coordinators)
        3 = Leaf specialists (no Task tool, cannot spawn)
        """
        if name in self.ROOT_AGENTS:
            return 0
        if name in self.COORDINATOR_AGENTS:
            return 1
        if not can_spawn:
            return 3  # Leaf node
        return 2  # Mid-level agent with spawning capability

    def _parse_references(self, name: str, agent) -> None:
        """Parse agent content to find references to other agents."""
        content = agent.content.lower()
        description = str(agent.description).lower() if agent.description else ""
        combined = f"{content} {description}"

        for other_name in self.agents.keys():
            if other_name == name:
                continue

            # Check if this agent's content mentions the other agent
            patterns = [
                rf"\b{re.escape(other_name)}\b",
                rf"\b{re.escape(other_name.replace('-', '_'))}\b",
                rf"\b{re.escape(other_name.replace('-', ' '))}\b",
            ]

            for pattern in patterns:
                if re.search(pattern, combined):
                    # This agent references the other agent
                    other_node = self.nodes.get(other_name)
                    this_node = self.nodes.get(name)

                    if other_node and this_node:
                        # If this agent has lower depth, it might spawn the other
                        if this_node.depth < other_node.depth:
                            if other_name not in this_node.children:
                                this_node.children.append(other_name)
                            if name not in other_node.parents:
                                other_node.parents.append(name)
                    break

    def _infer_siblings(self) -> None:
        """Infer sibling relationships based on depth and specialization."""
        # Group agents by depth
        by_depth: dict[int, list[str]] = {}
        for name, node in self.nodes.items():
            by_depth.setdefault(node.depth, []).append(name)

        # Agents at the same depth with same parents are siblings
        for depth, agents in by_depth.items():
            if depth == 0:
                continue  # Root has no siblings

            for name in agents:
                node = self.nodes[name]
                for other_name in agents:
                    if other_name == name:
                        continue
                    other_node = self.nodes[other_name]

                    # Same depth and overlapping parents = siblings
                    if node.parents and other_node.parents:
                        if set(node.parents) & set(other_node.parents):
                            if other_name not in node.siblings:
                                node.siblings.append(other_name)

                # Also consider same-type specialists as siblings
                if self._are_sibling_specialists(name, other_name):
                    if other_name not in node.siblings:
                        node.siblings.append(other_name)

    def _are_sibling_specialists(self, name1: str, name2: str) -> bool:
        """Check if two agents are likely sibling specialists."""
        # Language/framework specialists are siblings
        dev_suffixes = ["-dev", "-engineer", "-specialist"]
        for suffix in dev_suffixes:
            if name1.endswith(suffix) and name2.endswith(suffix):
                return True
        return False

    def get_depth(self, agent_name: str) -> int:
        """Get the depth of an agent."""
        node = self.nodes.get(agent_name)
        return node.depth if node else -1

    def find_parents(self, agent_name: str) -> list[str]:
        """Find agents that spawn this one."""
        node = self.nodes.get(agent_name)
        if not node:
            return []
        if node.parents:
            return node.parents

        # Infer parents based on depth
        parents = []
        for name, other_node in self.nodes.items():
            if other_node.depth < node.depth and other_node.can_spawn:
                parents.append(name)
        return parents[:3]  # Limit to top 3

    def find_children(self, agent_name: str) -> list[str]:
        """Find agents that this one spawns."""
        node = self.nodes.get(agent_name)
        if not node:
            return []
        return node.children

    def find_siblings(self, agent_name: str) -> list[str]:
        """Find agents at same level that work alongside this one."""
        node = self.nodes.get(agent_name)
        if not node:
            return []
        return node.siblings

    def get_node(self, agent_name: str) -> Optional[AgentNode]:
        """Get the node for an agent."""
        return self.nodes.get(agent_name)

    def build_tree(self) -> dict:
        """Build a hierarchical tree structure."""
        tree = {"name": "root", "children": {}}

        def add_to_tree(node_name: str, parent_path: list[str] = None):
            parent_path = parent_path or []
            node = self.nodes.get(node_name)
            if not node:
                return

            current = tree
            for p in parent_path:
                if p in current["children"]:
                    current = current["children"][p]

            if node_name not in current["children"]:
                current["children"][node_name] = {
                    "name": node_name,
                    "depth": node.depth,
                    "can_spawn": node.can_spawn,
                    "children": {},
                }

        # Add all nodes by depth
        for depth in range(4):
            for name, node in sorted(self.nodes.items(), key=lambda x: x[0]):
                if node.depth == depth:
                    if depth == 0:
                        add_to_tree(name, [])
                    else:
                        for parent in node.parents[:1]:  # Use first parent
                            add_to_tree(name, [parent])

        return tree

    def to_ascii_graph(self, agent_name: str, max_width: int = 50) -> str:
        """Generate ASCII visualization of agent relationships."""
        node = self.nodes.get(agent_name)
        if not node:
            return f"Agent '{agent_name}' not found"

        lines = []

        # Show parents (spawned by)
        if node.parents:
            lines.append("  SPAWNED BY:")
            for i, parent in enumerate(node.parents[:3]):
                parent_node = self.nodes.get(parent)
                depth_str = f"depth {parent_node.depth}" if parent_node else ""

                box_top = f"  {chr(0x250c)}{'─' * 25}{chr(0x2510)}"
                box_mid = f"  {chr(0x2502)} {parent:<23} {chr(0x2502)} {depth_str}"
                box_bot = f"  {chr(0x2514)}{'─' * 11}{chr(0x252c)}{'─' * 13}{chr(0x2518)}"

                lines.append(box_top)
                lines.append(box_mid)
                lines.append(box_bot)
                lines.append(f"              {chr(0x2502)}")

        # Show current agent
        box_top = f"  {chr(0x250c)}{'─' * 25}{chr(0x2510)}"
        box_mid = f"  {chr(0x2502)} {agent_name:<23} {chr(0x2502)} depth {node.depth} (YOU)"
        box_bot = f"  {chr(0x2514)}{'─' * 25}{chr(0x2518)}"
        lines.append(box_top)
        lines.append(box_mid)
        lines.append(box_bot)

        # Show siblings
        if node.siblings:
            lines.append("")
            lines.append("  WORKS WITH (same depth):")
            for sibling in node.siblings[:5]:
                sibling_node = self.nodes.get(sibling)
                companion = self._get_companion_label(agent_name, sibling)
                lines.append(f"  - {sibling} ({companion})")

        # Show children
        if node.children:
            lines.append("")
            lines.append("  DELEGATES TO:")
            for child in node.children[:5]:
                child_node = self.nodes.get(child)
                depth_str = f"depth {child_node.depth}" if child_node else ""
                lines.append(f"  - {child} ({depth_str})")
        elif not node.can_spawn:
            lines.append("")
            lines.append("  DELEGATES TO:")
            lines.append("  None (leaf node)")

        return "\n".join(lines)

    def _get_companion_label(self, agent1: str, agent2: str) -> str:
        """Get a label describing the relationship between two siblings."""
        # Try to infer relationship from names
        if "frontend" in agent1 and "backend" in agent2:
            return "backend companion"
        if "backend" in agent1 and "frontend" in agent2:
            return "frontend companion"
        if "-dev" in agent1 and "-dev" in agent2:
            return "language companion"
        if "test" in agent2:
            return "testing companion"
        if "review" in agent2:
            return "review companion"
        return "parallel worker"

    def get_agents_by_depth(self) -> dict[int, list[str]]:
        """Get agents grouped by depth."""
        by_depth: dict[int, list[str]] = {}
        for name, node in sorted(self.nodes.items(), key=lambda x: (x[1].depth, x[0])):
            by_depth.setdefault(node.depth, []).append(name)
        return by_depth

    def get_depth_label(self, depth: int) -> str:
        """Get a human-readable label for a depth level."""
        labels = {
            0: "Orchestrators",
            1: "Coordinators",
            2: "Mid-level",
            3: "Specialists (leaf)",
        }
        return labels.get(depth, f"Depth {depth}")
