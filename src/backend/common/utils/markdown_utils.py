"""Shared GFM table repair utilities (Bug 47810)."""

import re
from typing import List, Optional

# Matches a GFM delimiter cell: "---", ":--", "--:", ":-:".
_TABLE_DELIM_CELL_RE = re.compile(r"^\s*:?-+:?\s*$")


def reflow_collapsed_table_line(line: str) -> Optional[List[str]]:
    """Rebuild a GFM table flattened onto one line; return None if not collapsed."""
    if line.count("|") < 4 or "-" not in line:
        return None

    first = line.index("|")
    prefix = line[:first].rstrip()
    raw = line[first:].rstrip()

    tokens = raw.split("|")
    if tokens and tokens[0].strip() == "":
        tokens = tokens[1:]
    if tokens and tokens[-1].strip() == "":
        tokens = tokens[:-1]
    if not tokens:
        return None

    # Whitespace-only tokens mark the boundary between flattened rows.
    rows: List[List[str]] = []
    current: List[str] = []
    for tok in tokens:
        if tok.strip() == "":
            if current:
                rows.append(current)
                current = []
        else:
            current.append(tok)
    if current:
        rows.append(current)

    # Require a header plus a delimiter row; leaves well-formed tables untouched.
    if len(rows) < 2 or not all(_TABLE_DELIM_CELL_RE.match(c) for c in rows[1]):
        return None

    n = len(rows[1])
    if n == 0 or len(rows[0]) != n:
        return None

    rendered = ["| " + " | ".join(cell.strip() for cell in row) + " |" for row in rows]

    result: List[str] = []
    if prefix:
        result.append(prefix)
        result.append("")  # Blank line so GFM starts a fresh table block.
    result.extend(rendered)
    return result


def normalize_markdown_tables(text: str) -> str:
    """Repair collapsed GFM tables; non-table text is returned unchanged."""
    if not text or "|" not in text or "-" not in text:
        return text

    out: List[str] = []
    for line in text.split("\n"):
        reflowed = reflow_collapsed_table_line(line)
        if reflowed is None:
            out.append(line)
        else:
            out.extend(reflowed)
    return "\n".join(out)
