"""Base menu class with common functionality."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.colors import Colors


class BaseMenu:
    """Base class for all interactive menu screens."""

    def __init__(self, width: int = 55):
        self.width = width
        self.colors = Colors
        self.box = Colors.box_chars()

    def clear_screen(self) -> None:
        """Clear the terminal screen using subprocess for security."""
        if sys.platform == 'win32':
            subprocess.run(['cmd', '/c', 'cls'], check=False)
        else:
            subprocess.run(['clear'], check=False)

    def draw_box(self, title: str, subtitle: str = "") -> None:
        """Draw a header box with title and optional subtitle."""
        c = self.colors
        b = self.box

        # Top border
        top = f"{b['top_left']}{b['horizontal'] * (self.width - 2)}{b['top_right']}"
        print(c.colorize(top, c.CYAN))

        # Title line
        title_display = f"  {title}"
        padding = self.width - len(title_display) - len(subtitle) - 3
        if subtitle:
            line = f"{b['vertical']}{title_display}{' ' * padding}{subtitle} {b['vertical']}"
        else:
            line = f"{b['vertical']}{title_display}{' ' * (self.width - len(title_display) - 2)}{b['vertical']}"
        print(c.colorize(line, c.CYAN, c.BOLD))

        # Bottom border
        bottom = f"{b['bottom_left']}{b['horizontal'] * (self.width - 2)}{b['bottom_right']}"
        print(c.colorize(bottom, c.CYAN))
        print()  # Empty line after header

    def draw_section(self, title: str) -> None:
        """Draw a section header."""
        c = self.colors
        print(f"\n  {c.colorize(title, c.YELLOW, c.BOLD)}")

    def draw_option(self, key: str, label: str, description: str = "", indent: int = 2) -> None:
        """Draw a menu option."""
        c = self.colors
        prefix = " " * indent
        key_display = c.colorize(f"[{key}]", c.CYAN, c.BOLD)
        if description:
            print(f"{prefix}{key_display} {label}")
            print(f"{prefix}    {c.colorize(description, c.DIM)}")
        else:
            print(f"{prefix}{key_display} {label}")

    def draw_item(self, label: str, value: str = "", indent: int = 2) -> None:
        """Draw an informational item."""
        c = self.colors
        prefix = " " * indent
        if value:
            print(f"{prefix}{c.colorize(label, c.DIM)}: {value}")
        else:
            print(f"{prefix}{label}")

    def draw_status(self, label: str, is_ok: bool, detail: str = "") -> None:
        """Draw a status line with check/cross indicator."""
        c = self.colors
        b = self.box
        indicator = c.colorize(b['check'], c.GREEN) if is_ok else c.colorize(b['cross_mark'], c.RED)
        status = c.colorize("installed", c.GREEN) if is_ok else c.colorize("not found", c.DIM)
        detail_str = f"  {c.colorize(detail, c.DIM)}" if detail else ""
        print(f"  {indicator} {label:<20} {status}{detail_str}")

    def draw_separator(self) -> None:
        """Draw a horizontal separator."""
        c = self.colors
        print(c.colorize(f"  {'─' * (self.width - 4)}", c.DIM))

    def prompt(self, text: str = ">") -> str:
        """Display a prompt and get user input."""
        c = self.colors
        try:
            return input(f"\n  {c.colorize(text, c.CYAN, c.BOLD)} ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return 'q'

    def prompt_choice(self, options: list, multi: bool = False, allow_back: bool = True) -> list[int]:
        """
        Prompt user to select from options.
        Returns list of selected indices (0-based).
        """
        c = self.colors

        if multi:
            hint = c.colorize("(comma-separated, or 'a' for all)", c.DIM)
            print(f"\n  {hint}")

        if allow_back:
            print(f"\n  {c.colorize('[q] Back', c.DIM)}")

        response = self.prompt()

        if response.lower() in ('q', 'quit', 'back', 'exit'):
            return []

        if multi and response.lower() == 'a':
            return list(range(len(options)))

        try:
            if multi:
                indices = [int(x.strip()) - 1 for x in response.split(',')]
            else:
                indices = [int(response) - 1]

            # Validate indices
            valid = [i for i in indices if 0 <= i < len(options)]
            return valid
        except ValueError:
            return []

    def prompt_text(self, label: str, default: str = "") -> str:
        """Prompt for text input with optional default."""
        c = self.colors
        if default:
            prompt_str = f"{label} [{c.colorize(default, c.DIM)}]"
        else:
            prompt_str = label

        response = self.prompt(f"{prompt_str}:")
        return response if response else default

    def prompt_confirm(self, message: str, default: bool = True) -> bool:
        """Prompt for yes/no confirmation."""
        c = self.colors
        default_str = "Y/n" if default else "y/N"
        response = self.prompt(f"{message} [{default_str}]")

        if not response:
            return default

        return response.lower() in ('y', 'yes', 'true', '1')

    def wait_for_key(self, message: str = "Press Enter to continue...") -> None:
        """Wait for user to press a key."""
        c = self.colors
        try:
            input(f"\n  {c.colorize(message, c.DIM)}")
        except (KeyboardInterrupt, EOFError):
            pass

    def print_success(self, message: str) -> None:
        """Print a success message."""
        c = self.colors
        b = self.box
        print(f"  {c.colorize(b['check'], c.GREEN)} {message}")

    def print_error(self, message: str) -> None:
        """Print an error message."""
        c = self.colors
        b = self.box
        print(f"  {c.colorize(b['cross_mark'], c.RED)} {message}")

    def print_info(self, message: str) -> None:
        """Print an info message."""
        c = self.colors
        print(f"  {c.colorize('*', c.CYAN)} {message}")

    def run(self) -> Optional[str]:
        """
        Run the menu loop.
        Should be overridden by subclasses.
        Returns the action/result or None to exit.
        """
        raise NotImplementedError("Subclasses must implement run()")
