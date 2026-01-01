"""
This module provides functions for printing colored text and showing differences between two texts.
The main functions are `showDiff`.
"""

# ---
import difflib
import re
import functools

from collections import abc
from difflib import _format_range_unified as format_range_unified
from itertools import zip_longest
from collections.abc import Iterable, Sequence

import logging

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def get_color_table() -> dict[str, str]:
    # new Define the color codes for different colors
    color_numbers = {
        # 'lightred': 101,
        # 'lightgreen': 102,
        # 'lightpurple': 105,
        # 'lightyellow': 103,
        # 'lightblue': 104,
        # 'lightcyan': 106,
        # 'aqua': 106,
        # 'lightaqua': 107,
        # 'lightwhite': 107,
        # 'lightgray': 107,
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
    color_table = {x : f"\033[{v}m%s\033[00m" for x, v in color_numbers.items()}

    # Add light versions of the colors to the color table
    for color in ["purple", "yellow", "blue", "red", "green", "cyan", "gray"]:
        color_table[f"light{color}"] = color_table.get(color, 0)

    # Add some additional color names to the color table
    color_table["aqua"] = color_table.get("cyan", 0)
    color_table["lightaqua"] = color_table.get("cyan", 0)
    color_table["lightgrey"] = color_table.get("gray", 0)
    color_table["grey"] = color_table.get("gray", 0)
    color_table["lightwhite"] = color_table.get("gray", 0)
    color_table["light"] = 0

    return color_table


def make_str(textm):
    """
    Prints the given text with color formatting.

    The text can contain color tags like '<<color>>' where 'color' is the name of the color.
    The color will be applied to the text that follows the tag, until the end of the string or until a '<<default>>' tag is found.

    If 'noprint' is in sys.argv, the function will return without printing anything.

    :param textm: The text to print. Can contain color tags.
    """
    color_table = get_color_table()

    # Define a pattern for color tags
    _color_pat = r"((:?\w+|previous);?(:?\w+|previous)?)"
    # Compile a regex for color tags
    colorTagR = re.compile(rf"(?:\03{{|<<){_color_pat}(?:}}|>>)")

    # Initialize a stack for color tags
    color_stack = ["default"]

    # If the input is not a string, print it as is and return
    if not isinstance(textm, str):
        return textm

    # If the text does not contain any color tags, print it as is and return
    if textm.find("\03") == -1 and textm.find("<<") == -1:
        return textm

    # Split the text into parts based on the color tags
    text_parts = colorTagR.split(textm) + ["default"]

    # Enumerate the parts for processing
    enu = enumerate(zip(text_parts[::4], text_parts[1::4]))

    # Initialize the string to be printed
    toprint = ""

    # Process each part of the text
    for _, (text, next_color) in enu:
        # Get the current color from the color stack
        # print(f"i: {index}, text: {text}, next_color: {next_color}")
        # ---
        current_color = color_stack[-1]

        # If the next color is 'previous', pop the color stack to get the previous color
        if next_color == "previous":
            if len(color_stack) > 1:  # keep the last element in the stack
                color_stack.pop()
            next_color = color_stack[-1]
        else:
            # If the next color is not 'previous', add it to the color stack
            color_stack.append(next_color)

        # Get the color code for the current color
        cc = color_table.get(current_color, "")

        # If the color code is not empty, apply it to the text
        if cc:
            text = cc % text

        # Add the colored text to the string to be printed
        toprint += text

    # Print the final colored text
    return toprint


class Hunk:
    """One change hunk between a and b.

    Note: parts of this code are taken from by difflib.get_grouped_opcodes().

    """

    APPR = 1
    NOT_APPR = -1
    PENDING = 0

    def __init__(self, a: str | Sequence[str], b: str | Sequence[str], grouped_opcode: Sequence[tuple[str, int, int, int, int]]) -> None:
        """
        Initializer.

        :param a: sequence of lines
        :param b: sequence of lines
        :param grouped_opcode: list of 5-tuples describing how to turn a into
            b. It has the same format as returned by difflib.get_opcodes().
        """
        self.a = a
        self.b = b
        self.group = grouped_opcode
        self.colors = {
            "+": "lightgreen",
            "-": "lightred",
        }
        self.bg_colors = {
            "+": "lightgreen",
            "-": "lightred",
        }

        self.diff = list(self.create_diff())
        self.diff_plain_text = "".join(self.diff)
        self.diff_text = "".join(self.format_diff())

        first, last = self.group[0], self.group[-1]
        self.a_rng = (first[1], last[2])
        self.b_rng = (first[3], last[4])

        self.header = self.get_header()
        self.diff_plain_text = f"{self.header}\n{self.diff_plain_text}"
        self.diff_text = self.diff_text

        self.reviewed = self.PENDING

        self.pre_context = 0
        self.post_context = 0

    def get_header(self) -> str:
        """Provide header of unified diff."""
        return f"{self.get_header_text(self.a_rng, self.b_rng)}\n"

    @staticmethod
    def get_header_text(a_rng: tuple[int, int], b_rng: tuple[int, int], affix: str = "@@") -> str:
        """Provide header for any ranges."""
        a_rng = format_range_unified(*a_rng)
        b_rng = format_range_unified(*b_rng)
        return f"{affix} -{a_rng} +{b_rng} {affix}"

    def create_diff(self) -> Iterable[str]:
        """Generator of diff text for this hunk, without formatting."""

        # make sure each line ends with '\n' to prevent
        # behaviour like https://bugs.python.org/issue2142
        def check_line(line: str) -> str:
            return line if line.endswith("\n") else f"{line}\n"

        for tag, i1, i2, j1, j2 in self.group:
            # equal/delete/insert add additional space after the sign as it's
            # what difflib.ndiff does do too.
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
        """Color diff lines."""
        diff = iter(self.diff)

        fmt = ""
        line1, line2 = "", next(diff)
        for line in diff:
            fmt, line1, line2 = line1, line2, line
            # do not show lines starting with '?'.
            if line1.startswith("?"):
                continue
            if line2.startswith("?"):
                yield self.color_line(line1, line2)
                # do not try to reuse line2 as format at next iteration
                # if already used for an added line.
                if line1.startswith("+"):
                    line2 = ""
                continue
            if line1.startswith("-"):
                # Color whole line to be removed.
                yield self.color_line(line1)
            elif line1.startswith("+"):
                # Reuse last available fmt as diff line, if possible,
                # or color whole line to be added.
                fmt = fmt if fmt.startswith("?") else ""
                fmt = fmt[: min(len(fmt), len(line1))]
                fmt = fmt if fmt else None
                yield self.color_line(line1, fmt)

        # handle last line
        # If line line2 is removed, color the whole line.
        # If line line2 is added, check if line1 is a '?-type' line, to prevent
        # the entire line line2 to be colored (see T130572).
        # The case where line2 start with '?' has been covered already.
        if line2.startswith("-"):
            # Color whole line to be removed.
            yield self.color_line(line2)
        elif line2.startswith("+"):
            # Reuse last available line1 as diff line, if possible,
            # or color whole line to be added.
            fmt = line1 if line1.startswith("?") else ""
            fmt = fmt[: min(len(fmt), len(line2))]
            fmt = fmt if fmt else None
            yield self.color_line(line2, fmt)

    def color_line(self, line: str, line_ref: str | None = None) -> str:
        """Color line characters.

        If line_ref is None, the whole line is colored.
        If line_ref[i] is not blank, line[i] is colored.
        Color depends if line starts with +/-.

        line_ref: string.
        """
        color = line[0]

        if line_ref is None:
            if color in self.colors:
                # colored_line = color_format('{color}{0}{default}',line, color=self.colors[color])
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
                    apply_color = self.colors[color] if char != " " else f"default;{self.bg_colors[color]}"
                    # char_tagged = color_format('{color}{0}', char, color=apply_color)
                    char_tagged = f"<<{apply_color}>>"
                    char_tagged += char
                    color_closed = False
            elif char_ref == " ":
                # char_tagged = color_format('{default}{0}', char)
                char_tagged = f"<<default>>{char}"
                color_closed = True
            colored_line += char_tagged

        if not color_closed:
            # colored_line += color_format('{default}')
            colored_line += "<<default>>"

        return colored_line

    def __str__(self) -> str:
        """Return the diff as plain text."""
        return "".join(self.diff_plain_text)

    def __repr__(self) -> str:
        """Return a reconstructable representation."""
        # TODO
        return f"{self.__class__.__name__}(a, b, {self.group})"


class _Superhunk(abc.Sequence):
    def __init__(self, hunks: Sequence[Hunk]) -> None:
        self._hunks = hunks
        self.a_rng = (self._hunks[0].a_rng[0], self._hunks[-1].a_rng[1])
        self.b_rng = (self._hunks[0].b_rng[0], self._hunks[-1].b_rng[1])
        self.pre_context = self._hunks[0].pre_context
        self.post_context = self._hunks[0].post_context

    def __getitem__(self, idx: int) -> Hunk:
        return self._hunks[idx]

    def __len__(self) -> int:
        return len(self._hunks)


def get_header_text(a_rng: tuple[int, int], b_rng: tuple[int, int], affix: str = "@@") -> str:
    """Provide header for any ranges."""
    a_rng = format_range_unified(*a_rng)
    b_rng = format_range_unified(*b_rng)
    return f"{affix} -{a_rng} +{b_rng} {affix}"


class PatchManager:
    def __init__(self, text_a: str, text_b: str, context: int = 0) -> None:
        self.a = text_a.splitlines(True)
        self.b = text_b.splitlines(True)

        # groups and hunk have same order (one hunk correspond to one group).
        s = difflib.SequenceMatcher(None, self.a, self.b)
        self.groups = list(s.get_grouped_opcodes(0))
        self.hunks = []
        previous_hunk = None
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
        # blocks are a superset of hunk, as include also parts not
        # included in any hunk.
        self.blocks = self.get_blocks()
        self.context = context
        self._super_hunks = self._generate_super_hunks()

    def get_blocks(self) -> list[tuple[int, tuple[int, int], tuple[int, int]]]:
        """Return list with blocks of indexes.

        Format of each block::

            [-1, (i1, i2), (-1, -1)] -> block a[i1:i2] does not change from
                a to b then is there is no corresponding hunk.
            [hunk index, (i1, i2), (j1, j2)] -> block a[i1:i2] becomes b[j1:j2]
        """
        blocks = []
        i2 = 0
        for hunk_idx, group in enumerate(self.groups):
            first, last = group[0], group[-1]
            i1, prev_i2, i2 = first[1], i2, last[2]

            # there is a section of unchanged text before this hunk.
            if prev_i2 < i1:
                rng = (-1, (prev_i2, i1), (-1, -1))
                blocks.append(rng)

            rng = (hunk_idx, (first[1], last[2]), (first[3], last[4]))
            blocks.append(rng)

        # there is a section of unchanged text at the end of a, b.
        if i2 < len(self.a):
            rng = (-1, (i2, len(self.a)), (-1, -1))
            blocks.append(rng)

        return blocks

    def print_hunks(self) -> None:
        """Print the headers and diff texts of all hunks to the output."""
        if self.hunks:
            output("\n".join(self._generate_diff(super_hunk) for super_hunk in self._super_hunks))

    def _generate_super_hunks(self, hunks: Iterable[Hunk] | None = None) -> list[_Superhunk]:
        if hunks is None:
            hunks = self.hunks

        if not hunks:
            return []

        if self.context:
            # Determine if two hunks are connected by self.context
            super_hunk = []
            super_hunks = [super_hunk]
            for hunk in hunks:
                # self.context * 2, because if self.context is 2 the hunks
                # would be directly adjacent when 4 lines in between and for
                # anything below 4 they share lines.
                # not super_hunk == first hunk as any other super_hunk is
                # created with one hunk
                if not super_hunk or hunk.pre_context <= self.context * 2:
                    # previous hunk has shared/adjacent self.context lines
                    super_hunk += [hunk]
                else:
                    super_hunk = [hunk]
                    super_hunks += [super_hunk]
        else:
            super_hunks = [[hunk] for hunk in hunks]
        return [_Superhunk(sh) for sh in super_hunks]

    def _get_context_range(self, super_hunk: _Superhunk) -> tuple[tuple[int, int], tuple[int, int]]:
        """Dynamically determine context range for a super hunk."""
        a0, a1 = super_hunk.a_rng
        b0, b1 = super_hunk.b_rng
        return ((a0 - min(super_hunk.pre_context, self.context), a1 + min(super_hunk.post_context, self.context)), (b0 - min(super_hunk.pre_context, self.context), b1 + min(super_hunk.post_context, self.context)))

    def _generate_diff(self, hunks: _Superhunk) -> str:
        """Generate a diff text for the given hunks."""

        def extend_context(start: int, end: int) -> str:
            """Add context lines."""
            return "".join(f"  {line.rstrip()}\n" for line in self.a[start:end])

        context_range = self._get_context_range(hunks)
        a11 = get_header_text(*context_range)
        a22 = extend_context(context_range[0][0], hunks[0].a_rng[0])
        # OutPut = color_format('{aqua}{0}{default}\n{1}',a11,a22)
        OutPut = f"<<aqua>>{a11}<<default>>\n{a22}"
        previous_hunk = None
        for hunk in hunks:
            if previous_hunk:
                OutPut += extend_context(previous_hunk.a_rng[1], hunk.a_rng[0])
            previous_hunk = hunk
            OutPut += hunk.diff_text
        OutPut += extend_context(hunks[-1].a_rng[1], context_range[0][1])
        return OutPut


def output(textm, *kwargs):
    print(make_str(textm))


def showDiff(text_a: str, text_b: str, context: int = 0) -> None:
    """
    Output a string showing the differences between text_a and text_b.

    The differences are highlighted (only on compatible systems) to show which
    changes were made.
    """
    PatchManager(text_a, text_b, context=context).print_hunks()


def show_diff(old_text, new_text):
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile='before', tofile='after', lineterm='')
    diff_text = ''.join(diff)

    if diff_text:
        logger.info(f"Diff:\n{diff_text}")
    else:
        logger.info("No changes detected.")


__all__ = [
    "make_str",
    "showDiff",
    "show_diff",
]
