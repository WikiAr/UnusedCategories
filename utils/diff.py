"""
Diff Utilities for Wikipedia Bot Applications.

This module provides utilities for computing and displaying differences between
text strings, with colorized output for terminal display. It implements a
unified diff format similar to what version control systems use.

The module includes:
- Color formatting using ANSI escape codes
- Unified diff generation with hunk grouping
- Colorized output for additions (green) and deletions (red)

Example:
    Basic usage::

        from utils.diff import showDiff, make_str

        # Show a colorized diff
        showDiff("old text", "new text")

        # Format a string with colors
        colored = make_str("<<green>>Success<<default>>")
        print(colored)

Attributes:
    logger: Module-level logger for diff operations.

Notes:
    - Color output requires ANSI-compatible terminal
    - The Hunk class represents a single change region in the diff
    - PatchManager orchestrates the diff generation process

"""

from __future__ import annotations

import difflib
import functools
import re
from collections import abc
from collections.abc import Iterable, Sequence
from difflib import _format_range_unified as format_range_unified
from itertools import zip_longest
from typing import TYPE_CHECKING, Any

import logging

if TYPE_CHECKING:
    from typing import Final, Optional

logger = logging.getLogger(__name__)


# Type alias for opcode tuples used by difflib
# Format: (tag: str, i1: int, i2: int, j1: int, j2: int)
OpcodeTuple = tuple[str, int, int, int, int]


@functools.lru_cache(maxsize=1)
def get_color_table() -> dict[str, str]:
    """
    Generate a cached table of color name to ANSI escape code format strings.

    This function creates a mapping from human-readable color names to ANSI
    escape code format strings. The result is cached to avoid recomputing
    the table on every call.

    Returns:
        A dictionary mapping color names (str) to format strings (str).
        Each format string contains '%s' as a placeholder for the text
        to be colored.

    Example:
        >>> colors = get_color_table()
        >>> print(colors["red"] % "Error")
        \033[91mError\033[00m

    Note:
        The color codes use standard ANSI SGR (Select Graphic Rendition)
        sequences. Not all terminals support all colors.

    """
    # Define the ANSI color codes for different colors
    # These are 256-color mode codes for better color variety
    color_numbers: dict[str, int] = {
        "red": 91,
        "green": 92,
        "yellow": 93,
        "blue": 94,
        "purple": 95,
        "cyan": 96,
        "white": 97,
        "black": 98,
        "grey": 99,
        "gray": 100,
        "underline": 4,
        "invert": 7,
        "blink": 5,
        "lightblack": 108,
        "bold": 1,
    }

    # Create format strings for each color
    color_table: dict[str, str] = {
        name: f"\033[{code}m%s\033[00m"
        for name, code in color_numbers.items()
    }

    # Add light versions of colors (these use the same codes as base colors)
    for color in ["purple", "yellow", "blue", "red", "green", "cyan", "gray"]:
        color_table[f"light{color}"] = color_table.get(color, "%s")

    # Add alternative names for colors
    color_table["aqua"] = color_table.get("cyan", "%s")
    color_table["lightaqua"] = color_table.get("cyan", "%s")
    color_table["lightgrey"] = color_table.get("gray", "%s")
    color_table["grey"] = color_table.get("gray", "%s")
    color_table["lightwhite"] = color_table.get("gray", "%s")
    color_table["light"] = "%s"  # No-op for "light" alone

    return color_table


def make_str(textm: Any) -> Any:
    """
    Format text with color codes and return the resulting string.

    This function processes text containing color tags (e.g., <<green>>,
    <<red>>) and converts them to ANSI escape codes. The color formatting
    uses a stack-based approach to handle nested colors.

    Supported color tags:
        - <<color>>: Apply color until <<default>> or end of string
        - <<previous>>: Return to the previous color on the stack
        - \03{color} or <<color>>: Alternative syntax

    Args:
        textm: The text to format. If not a string, returned unchanged.

    Returns:
        The text with color tags replaced by ANSI escape codes.
        Non-string inputs are returned unchanged.

    Example:
        >>> make_str("<<green>>Success<<default>>")
        '\\033[92mSuccess\\033[00m'

        >>> make_str("<<red>>Error: <<default>><<yellow>>warning<<default>>")
        # Returns string with red "Error: " and yellow "warning"

    Note:
        - The function uses a stack to track color state
        - Colors are applied until explicitly reset with <<default>>
        - Non-string inputs are returned as-is for convenience

    """
    color_table = get_color_table()

    # Define pattern for color tags: <<color>>, \03{color}, etc.
    _color_pat = r"((:?\w+|previous);?(:?\w+|previous)?)"
    colorTagR = re.compile(rf"(?:\03{{|<<){_color_pat}(?:}}|>>)")

    # Initialize color stack with default
    color_stack: list[str] = ["default"]

    # Return non-strings unchanged
    if not isinstance(textm, str):
        return textm

    # Fast path: no color tags in text
    if textm.find("\03") == -1 and textm.find("<<") == -1:
        return textm

    # Split text by color tags and add terminator
    text_parts = colorTagR.split(textm) + ["default"]

    # Process parts in groups of 4: (before_tag, full_match, color, semicolon_part)
    enu = enumerate(zip(text_parts[::4], text_parts[1::4]))

    toprint = ""

    for _, (text, next_color) in enu:
        current_color = color_stack[-1]

        # Handle "previous" color (pop from stack)
        if next_color == "previous":
            if len(color_stack) > 1:
                color_stack.pop()
            next_color = color_stack[-1]
        else:
            color_stack.append(next_color)

        # Apply color formatting if valid
        cc = color_table.get(current_color, "")
        if cc:
            text = cc % text

        toprint += text

    return toprint


class Hunk:
    """
    Represents a single change hunk (contiguous region of changes) in a diff.

    A hunk is a group of related changes that are close enough together to
    be displayed as a unit. This class handles the generation and colorization
    of diff output for a single hunk.

    Attributes:
        APPR: Constant for approved hunks (value 1)
        NOT_APPR: Constant for rejected hunks (value -1)
        PENDING: Constant for unreviewed hunks (value 0)
        a: Original text lines
        b: Modified text lines
        group: The opcode group defining the changes
        diff: List of diff lines (plain text)
        diff_plain_text: Combined plain text diff
        diff_text: Combined colorized diff
        a_rng: Range in original text (start, end)
        b_rng: Range in modified text (start, end)
        header: The hunk header line
        reviewed: Review status (APPR, NOT_APPR, or PENDING)

    Example:
        >>> import difflib
        >>> a = ["line1\\n", "line2\\n"]
        >>> b = ["line1\\n", "modified\\n"]
        >>> s = difflib.SequenceMatcher(None, a, b)
        >>> groups = list(s.get_grouped_opcodes(0))
        >>> hunk = Hunk(a, b, groups[0])

    """

    # Review status constants
    APPR: int = 1
    NOT_APPR: int = -1
    PENDING: int = 0

    def __init__(
        self,
        a: str | Sequence[str],
        b: str | Sequence[str],
        grouped_opcode: Sequence[OpcodeTuple],
    ) -> None:
        """
        Initialize a Hunk with the original and modified text and opcode group.

        Args:
            a: The original text as a sequence of lines.
            b: The modified text as a sequence of lines.
            grouped_opcode: A sequence of 5-tuples from difflib describing
                how to transform 'a' into 'b'. Format:
                (tag, i1, i2, j1, j2) where:
                - tag: 'equal', 'delete', 'insert', or 'replace'
                - i1, i2: Range in 'a' affected
                - j1, j2: Range in 'b' affected

        """
        self.a = a
        self.b = b
        self.group = grouped_opcode

        # Color configuration for diff output
        self.colors: dict[str, str] = {
            "+": "lightgreen",
            "-": "lightred",
        }
        self.bg_colors: dict[str, str] = {
            "+": "lightgreen",
            "-": "lightred",
        }

        # Generate diff output
        self.diff = list(self.create_diff())
        self.diff_plain_text = "".join(self.diff)
        self.diff_text = "".join(self.format_diff())

        # Calculate ranges
        first, last = self.group[0], self.group[-1]
        self.a_rng = (first[1], last[2])
        self.b_rng = (first[3], last[4])

        # Generate header
        self.header = self.get_header()
        self.diff_plain_text = f"{self.header}\n{self.diff_plain_text}"
        self.diff_text = self.diff_text

        # Review status
        self.reviewed = self.PENDING

        # Context tracking
        self.pre_context = 0
        self.post_context = 0

    def get_header(self) -> str:
        """
        Generate the unified diff header for this hunk.

        Returns:
            The hunk header line in unified diff format
            (e.g., "@@ -1,5 +1,6 @@")

        """
        return f"{self.get_header_text(self.a_rng, self.b_rng)}\n"

    @staticmethod
    def get_header_text(
        a_rng: tuple[int, int],
        b_rng: tuple[int, int],
        affix: str = "@@",
    ) -> str:
        """
        Generate a unified diff header for given ranges.

        Args:
            a_rng: Range in original text as (start, end).
            b_rng: Range in modified text as (start, end).
            affix: The marker to use around the ranges. Default "@@".

        Returns:
            The formatted header string.

        """
        a_rng_str = format_range_unified(*a_rng)
        b_rng_str = format_range_unified(*b_rng)
        return f"{affix} -{a_rng_str} +{b_rng_str} {affix}"

    def create_diff(self) -> Iterable[str]:
        """
        Generate plain text diff lines for this hunk.

        Yields:
            Diff lines with standard prefixes:
            - "  " for unchanged lines
            "- " for deleted lines
            - "+ " for added lines
            - "? " for character-level diff indicators

        Note:
            Each line is guaranteed to end with a newline character.

        """
        def check_line(line: str) -> str:
            """Ensure line ends with newline."""
            return line if line.endswith("\n") else f"{line}\n"

        for tag, i1, i2, j1, j2 in self.group:
            if tag == "equal":
                for line in self.a[i1:i2]:
                    yield f"  {check_line(line)}"
            elif tag == "delete":
                for line in self.a[i1:i2]:
                    yield f"- {check_line(line)}"
            elif tag == "insert":
                for line in self.b[j1:j2]:
                    yield f"+ {check_line(line)}"
            elif tag == "replace":
                for line in difflib.ndiff(self.a[i1:i2], self.b[j1:j2]):
                    yield check_line(line)

    def format_diff(self) -> Iterable[str]:
        """
        Generate colorized diff lines.

        Yields:
            Diff lines with ANSI color codes applied:
            - Green for additions
            - Red for deletions

        """
        diff = iter(self.diff)

        fmt = ""
        line1, line2 = "", next(diff)

        for line in diff:
            fmt, line1, line2 = line1, line2, line

            # Skip lines starting with '?' (character-level indicators)
            if line1.startswith("?"):
                continue

            if line2.startswith("?"):
                yield self.color_line(line1, line2)
                if line1.startswith("+"):
                    line2 = ""
                continue

            if line1.startswith("-"):
                yield self.color_line(line1)
            elif line1.startswith("+"):
                fmt = fmt if fmt.startswith("?") else ""
                fmt = fmt[: min(len(fmt), len(line1))]
                fmt = fmt if fmt else None
                yield self.color_line(line1, fmt)

        # Handle the last line
        if line2.startswith("-"):
            yield self.color_line(line2)
        elif line2.startswith("+"):
            fmt = line1 if line1.startswith("?") else ""
            fmt = fmt[: min(len(fmt), len(line2))]
            fmt = fmt if fmt else None
            yield self.color_line(line2, fmt)

    def color_line(self, line: str, line_ref: str | None = None) -> str:
        """
        Apply color formatting to a diff line.

        Args:
            line: The diff line to color (starts with + or -).
            line_ref: Optional reference line for character-level coloring.
                If None, the entire line is colored. If provided, only
                characters where line_ref has non-space are colored.

        Returns:
            The line with ANSI color codes applied.

        """
        color = line[0]

        if line_ref is None:
            if color in self.colors:
                colored_line = f"<<{self.colors[color]}>>"
                colored_line += f"{line}<<default>>"
                return colored_line
            return line

        colored_line = ""
        color_closed = True

        for char, char_ref in zip_longest(line, line_ref.strip(), fillvalue=" "):
            char_tagged = char

            if color_closed:
                if char_ref != " ":
                    apply_color = (
                        self.colors[color]
                        if char != " "
                        else f"default;{self.bg_colors[color]}"
                    )
                    char_tagged = f"<<{apply_color}>>"
                    char_tagged += char
                    color_closed = False
            elif char_ref == " ":
                char_tagged = f"<<default>>{char}"
                color_closed = True

            colored_line += char_tagged

        if not color_closed:
            colored_line += "<<default>>"

        return colored_line

    def __str__(self) -> str:
        """Return the plain text diff representation."""
        return "".join(self.diff_plain_text)

    def __repr__(self) -> str:
        """Return a reconstructable representation."""
        return f"{self.__class__.__name__}(a, b, {self.group})"


class _Superhunk(abc.Sequence):
    """
    A sequence of Hunk objects that are displayed together.

    Superhunks group related hunks that should be displayed as a unit,
    typically when they are close enough to share context lines.

    Attributes:
        _hunks: The list of Hunk objects in this superhunk.
        a_rng: Combined range in original text.
        b_rng: Combined range in modified text.
        pre_context: Number of context lines before the first hunk.
        post_context: Number of context lines after the last hunk.

    """

    def __init__(self, hunks: Sequence[Hunk]) -> None:
        """
        Initialize a Superhunk from a sequence of hunks.

        Args:
            hunks: Sequence of Hunk objects to group together.

        """
        self._hunks = hunks
        self.a_rng = (self._hunks[0].a_rng[0], self._hunks[-1].a_rng[1])
        self.b_rng = (self._hunks[0].b_rng[0], self._hunks[-1].b_rng[1])
        self.pre_context = self._hunks[0].pre_context
        self.post_context = self._hunks[-1].post_context

    def __getitem__(self, idx: int) -> Hunk:
        """Get a hunk by index."""
        return self._hunks[idx]

    def __len__(self) -> int:
        """Return the number of hunks in this superhunk."""
        return len(self._hunks)


def get_header_text(
    a_rng: tuple[int, int],
    b_rng: tuple[int, int],
    affix: str = "@@",
) -> str:
    """
    Generate a unified diff header for given ranges.

    This is a module-level version of Hunk.get_header_text for convenience.

    Args:
        a_rng: Range in original text as (start, end).
        b_rng: Range in modified text as (start, end).
        affix: The marker to use around the ranges.

    Returns:
        The formatted header string.

    """
    a_rng_str = format_range_unified(*a_rng)
    b_rng_str = format_range_unified(*b_rng)
    return f"{affix} -{a_rng_str} +{b_rng_str} {affix}"


class PatchManager:
    """
    Manages the generation and display of unified diffs between two texts.

    This class orchestrates the diff generation process, dividing the changes
    into hunks and superhunks for organized display.

    Attributes:
        a: Original text split into lines.
        b: Modified text split into lines.
        groups: Opcode groups from difflib.
        hunks: List of Hunk objects.
        blocks: List of change blocks with indices.
        context: Number of context lines to show around changes.
        _super_hunks: List of Superhunk objects.

    Example:
        >>> pm = PatchManager("old text", "new text")
        >>> pm.print_hunks()

    """

    def __init__(self, text_a: str, text_b: str, context: int = 0) -> None:
        """
        Initialize a PatchManager with original and modified texts.

        Args:
            text_a: The original text string.
            text_b: The modified text string.
            context: Number of unchanged context lines to show around each
                change. Defaults to 0 (no context).

        """
        self.a = text_a.splitlines(True)
        self.b = text_b.splitlines(True)

        # Generate opcode groups using difflib
        s = difflib.SequenceMatcher(None, self.a, self.b)
        self.groups = list(s.get_grouped_opcodes(0))

        # Create hunks from groups
        self.hunks: list[Hunk] = []
        previous_hunk: Optional[Hunk] = None

        for group in self.groups:
            hunk = Hunk(self.a, self.b, group)
            self.hunks.append(hunk)
            hunk.pre_context = hunk.a_rng[0]

            if previous_hunk:
                hunk.pre_context -= previous_hunk.a_rng[1]
                previous_hunk.post_context = hunk.pre_context

            previous_hunk = hunk

        if self.hunks:
            self.hunks[-1].post_context = len(self.a) - self.hunks[-1].a_rng[1]

        # Generate blocks (includes unchanged sections)
        self.blocks = self.get_blocks()
        self.context = context
        self._super_hunks = self._generate_super_hunks()

    def get_blocks(self) -> list[tuple[int, tuple[int, int], tuple[int, int]]]:
        """
        Generate a list of blocks representing changes and unchanged sections.

        Returns:
            List of blocks, where each block is a tuple:
            - (hunk_index, (a_start, a_end), (b_start, b_end)) for changes
            - (-1, (a_start, a_end), (-1, -1)) for unchanged sections

        """
        blocks: list[tuple[int, tuple[int, int], tuple[int, int]]] = []
        i2 = 0

        for hunk_idx, group in enumerate(self.groups):
            first, last = group[0], group[-1]
            i1, prev_i2, i2 = first[1], i2, last[2]

            # Add unchanged section before this hunk
            if prev_i2 < i1:
                rng = (-1, (prev_i2, i1), (-1, -1))
                blocks.append(rng)

            # Add the hunk itself
            rng = (hunk_idx, (first[1], last[2]), (first[3], last[4]))
            blocks.append(rng)

        # Add trailing unchanged section
        if i2 < len(self.a):
            rng = (-1, (i2, len(self.a)), (-1, -1))
            blocks.append(rng)

        return blocks

    def print_hunks(self) -> None:
        """Print all hunks to the output with colorization."""
        if self.hunks:
            output("\n".join(
                self._generate_diff(super_hunk)
                for super_hunk in self._super_hunks
            ))

    def _generate_super_hunks(
        self,
        hunks: Optional[Iterable[Hunk]] = None,
    ) -> list[_Superhunk]:
        """
        Group hunks into superhunks based on context distance.

        Args:
            hunks: Optional iterable of hunks to group. If None, uses
                self.hunks.

        Returns:
            List of _Superhunk objects.

        """
        if hunks is None:
            hunks = self.hunks

        if not hunks:
            return []

        hunks_list = list(hunks)

        if self.context:
            super_hunk: list[Hunk] = []
            super_hunks: list[list[Hunk]] = [super_hunk]

            for hunk in hunks_list:
                if not super_hunk or hunk.pre_context <= self.context * 2:
                    super_hunk.append(hunk)
                else:
                    super_hunk = [hunk]
                    super_hunks.append(super_hunk)
        else:
            super_hunks = [[hunk] for hunk in hunks_list]

        return [_Superhunk(sh) for sh in super_hunks]

    def _get_context_range(
        self,
        super_hunk: _Superhunk,
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """
        Calculate the context range for a superhunk.

        Args:
            super_hunk: The superhunk to calculate context for.

        Returns:
            A tuple of (a_range, b_range) where each range is (start, end).

        """
        a0, a1 = super_hunk.a_rng
        b0, b1 = super_hunk.b_rng

        return (
            (
                a0 - min(super_hunk.pre_context, self.context),
                a1 + min(super_hunk.post_context, self.context),
            ),
            (
                b0 - min(super_hunk.pre_context, self.context),
                b1 + min(super_hunk.post_context, self.context),
            ),
        )

    def _generate_diff(self, hunks: _Superhunk) -> str:
        """
        Generate the complete diff text for a superhunk.

        Args:
            hunks: The superhunk to generate diff text for.

        Returns:
            The colorized diff text.

        """
        def extend_context(start: int, end: int) -> str:
            """Add context lines to the output."""
            return "".join(
                f"  {line.rstrip()}\n" for line in self.a[start:end]
            )

        context_range = self._get_context_range(hunks)
        a11 = get_header_text(*context_range)
        a22 = extend_context(context_range[0][0], hunks[0].a_rng[0])

        output_text = f"<<aqua>>{a11}<<default>>\n{a22}"

        previous_hunk: Optional[Hunk] = None

        for hunk in hunks:
            if previous_hunk:
                output_text += extend_context(
                    previous_hunk.a_rng[1], hunk.a_rng[0]
                )
            previous_hunk = hunk
            output_text += hunk.diff_text

        output_text += extend_context(hunks[-1].a_rng[1], context_range[0][1])

        return output_text


def output(textm: Any, **kwargs: Any) -> None:
    """
    Print text with color formatting to stdout.

    This is a convenience function that formats text with make_str()
    and prints it.

    Args:
        textm: The text to print (may contain color tags).
        **kwargs: Additional keyword arguments (currently unused,
            reserved for future use like file= or end=).

    """
    print(make_str(textm))


def showDiff(text_a: str, text_b: str, context: int = 0) -> None:
    """
    Display a colorized unified diff between two text strings.

    This is the main entry point for displaying diffs. It creates a
    PatchManager and prints the resulting hunks.

    Args:
        text_a: The original text string.
        text_b: The modified text string.
        context: Number of unchanged context lines to show around changes.
            Defaults to 0.

    Example:
        >>> showDiff("Hello World", "Hello Python")
        # Shows a colorized diff with "World" deleted and "Python" added

    """
    PatchManager(text_a, text_b, context=context).print_hunks()


def show_diff(old_text: str, new_text: str) -> None:
    """
    Display a simple unified diff using Python's difflib.

    This is a simpler alternative to showDiff() that uses Python's
    built-in difflib.unified_diff without colorization.

    Args:
        old_text: The original text string.
        new_text: The modified text string.

    Example:
        >>> show_diff("old", "new")
        # Logs the diff using the module logger

    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile='before',
        tofile='after',
        lineterm=''
    )
    diff_text = ''.join(diff)

    if diff_text:
        logger.info(f"Diff:\n{diff_text}")
    else:
        logger.info("No changes detected.")


__all__ = [
    "make_str",
    "showDiff",
    "show_diff",
    "get_color_table",
    "Hunk",
    "PatchManager",
]
