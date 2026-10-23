"""Driver tree for a FAST model — the structure behind "don't calculate the same thing twice".

Design question: is there a structure that standardises exactly what is recalculated, with checks
that the same calculation is not made twice?

The answer is to stop INFERRING identity from a formula's text and start DECLARING it. Every
calculated quantity gets one canonical node name. Two rows cannot claim the same node, so a
re-derivation is a namespace collision caught at build time rather than a heuristic that guesses
from labels and produces false positives on two blocks that happen to share wording.

A node knows its label, unit, sheet row, and the nodes it reads. That graph IS the driver tree:
  * duplicate node   -> the same quantity derived twice
  * orphan node      -> calculated and never used
  * cycle            -> a circular definition, which FAST forbids outright
  * depth            -> how far a board number sits from the inputs it rests on
"""

from __future__ import annotations


class DriverTreeError(Exception):
    pass


class DriverTree:
    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.row_of: dict[int, str] = {}
        self.alias: dict[int, int] = {}  # a link row -> the row it points at

    # -- construction ----------------------------------------------------------------------
    def declare(
        self,
        node: str,
        *,
        label: str,
        unit: str,
        row: int,
        kind: str,
        reads: list[int] | None = None,
    ) -> None:
        if node in self.nodes:
            prior = self.nodes[node]
            raise DriverTreeError(
                f"driver {node!r} is already calculated at row {prior['row']} "
                f"({prior['label']!r}); row {row} ({label!r}) would derive it a second time. "
                f"FAST 1.01-07: calculate once, link thereafter."
            )
        self.nodes[node] = {
            "label": label,
            "unit": unit,
            "row": row,
            "kind": kind,
            "reads_rows": list(reads or []),
            "reads": [],
        }
        self.row_of[row] = node

    def points_at(self, link_row: int, source_row: int) -> None:
        """Record that a row is a LINK, not a driver. Links are pointers; the tree resolves
        through them to the calculation that actually defines the quantity. Without this every
        edge dies at the first link and the graph is all nodes and no structure."""
        self.alias[link_row] = source_row

    def _deref(self, row: int, _seen=None) -> int:
        _seen = _seen or set()
        while row in self.alias and row not in _seen:
            _seen.add(row)
            row = self.alias[row]
        return row

    def resolve(self) -> None:
        """Turn row references into node edges, once every node is declared."""
        for nd in self.nodes.values():
            # A row that reads ITSELF is a corkscrew reaching into the prior column -- a reference
            # backwards in time, not a circular definition. Dropping it here is what lets the
            # cycle check mean "this quantity is defined in terms of itself".
            nd["reads"] = sorted(
                {
                    self.row_of[self._deref(r)]
                    for r in nd["reads_rows"]
                    if self._deref(r) in self.row_of and self._deref(r) != nd["row"]
                }
            )

    # -- checks ----------------------------------------------------------------------------
    def cycles(self) -> list[list[str]]:
        seen, stack, out = set(), [], []

        def walk(n, path):
            if n in stack:
                out.append(path[path.index(n) :] + [n])
                return
            if n in seen:
                return
            seen.add(n)
            stack.append(n)
            for m in self.nodes.get(n, {}).get("reads", []):
                walk(m, path + [m])
            stack.pop()

        for n in self.nodes:
            walk(n, [n])
        return out

    def orphans(self, roots: set[str]) -> list[str]:
        used = {m for nd in self.nodes.values() for m in nd["reads"]}
        return sorted(n for n in self.nodes if n not in used and n not in roots)

    def depth(self, node: str) -> int:
        best, seen = 0, set()

        def walk(n, d):
            nonlocal best
            if n in seen:
                return
            seen.add(n)
            best = max(best, d)
            for m in self.nodes.get(n, {}).get("reads", []):
                walk(m, d + 1)

        walk(node, 0)
        return best

    # -- presentation ----------------------------------------------------------------------
    def mermaid(self, node: str, *, depth: int = 3) -> str:
        """The sub-tree under one driver, as Mermaid. Read top-down: what feeds this number."""
        lines, seen = ["flowchart TD"], set()
        ids: dict[str, str] = {}

        def sid(n):
            # Mermaid node ids cannot carry spaces or punctuation, and a block-scoped driver name
            # is "BLOCK TITLE::row". Keep the readable name in the LABEL, not the id.
            if n not in ids:
                ids[n] = f"n{len(ids)}"
            return ids[n]

        def walk(n, d):
            if d > depth or n in seen:
                return
            seen.add(n)
            nd = self.nodes[n]
            u = f"<br/><i>{nd['unit']}</i>" if nd["unit"] else ""
            lines.append(f'    {sid(n)}["{nd["label"]}{u}"]')
            if d >= depth:
                return  # depth counts LEVELS OF EDGES, not nodes visited
            for m in nd["reads"]:
                if m in self.nodes:
                    lines.append(f"    {sid(m)} --> {sid(n)}")
                    walk(m, d + 1)

        walk(node, 0)
        return "\n".join(lines)

    def report(self) -> str:
        out = [f"{len(self.nodes)} drivers declared"]
        deep = sorted(((self.depth(n), n) for n in self.nodes), reverse=True)[:5]
        out.append("  deepest: " + ", ".join(f"{n} ({d})" for d, n in deep))
        return "\n".join(out)
