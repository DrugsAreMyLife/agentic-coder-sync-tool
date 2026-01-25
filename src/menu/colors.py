"""ANSI color codes for terminal output - no emojis."""

import os
import sys


class Colors:
    """ANSI color codes for rich terminal output."""

    # Basic colors
    BLACK = '\033[30m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    HIDDEN = '\033[8m'
    STRIKETHROUGH = '\033[9m'

    # Reset
    RESET = '\033[0m'

    # Semantic colors
    HEADER = MAGENTA + BOLD
    SUCCESS = GREEN
    WARNING = YELLOW
    ERROR = RED
    INFO = CYAN
    MUTED = DIM
    HIGHLIGHT = YELLOW + BOLD
    SELECTION = CYAN + BOLD

    # Status indicators (no emojis)
    CHECK = SUCCESS + "[+]" + RESET
    CROSS = ERROR + "[-]" + RESET
    ARROW = CYAN + ">" + RESET
    DOT = DIM + "*" + RESET

    @classmethod
    def supports_color(cls) -> bool:
        """Check if the terminal supports colors."""
        # Check for NO_COLOR environment variable
        if os.environ.get('NO_COLOR'):
            return False

        # Check if stdout is a TTY
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return False

        # Check TERM environment variable
        term = os.environ.get('TERM', '')
        if term == 'dumb':
            return False

        return True

    @classmethod
    def strip_colors(cls, text: str) -> str:
        """Remove ANSI escape codes from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    @classmethod
    def colorize(cls, text: str, *colors: str) -> str:
        """Apply colors to text with automatic reset."""
        if not cls.supports_color():
            return text
        color_str = ''.join(colors)
        return f"{color_str}{text}{cls.RESET}"

    @classmethod
    def box_chars(cls) -> dict:
        """Return box-drawing characters."""
        return {
            'top_left': '\u250c',      # ┌
            'top_right': '\u2510',     # ┐
            'bottom_left': '\u2514',   # └
            'bottom_right': '\u2518',  # ┘
            'horizontal': '\u2500',    # ─
            'vertical': '\u2502',      # │
            'tee_right': '\u251c',     # ├
            'tee_left': '\u2524',      # ┤
            'tee_down': '\u252c',      # ┬
            'tee_up': '\u2534',        # ┴
            'cross': '\u253c',         # ┼
            'arrow_right': '\u25b6',   # ▶
            'arrow_down': '\u25bc',    # ▼
            'bullet': '\u2022',        # •
            'check': '\u2713',         # ✓
            'cross_mark': '\u2717',    # ✗
        }
