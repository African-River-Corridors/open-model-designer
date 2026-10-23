"""The module contract: what a reusable unit of model logic declares and carries.

A module declares its **ports** (the inputs it needs and the rows it gives, each with a unit) and
carries both halves of its logic: the **oracle** (plain Python) and the **formula half** (rows built
with the FAST block API). It carries its own **checks**, a **worked example**, a **golden case**
from an independent source, and a **scope note**. `omd.acceptance` is the CI gate that decides
whether a library module is accepted.

Ports wire by default to the standard line names in `omd.lines`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .lines import STANDARD_LINES

#: what may stand as the source of a golden case. "oracle" and "self" are not independent.
INDEPENDENT_KINDS = frozenset(
    {"hand-calculation", "published-example", "statute-worked-example", "third-party-tool"}
)


@dataclass(frozen=True)
class Port:
    name: str
    unit: str
    kind: str = "series"  # "series" (one value per period) or "scalar"
    line: str | None = None  # standard line name; defaults to `name` when `name` is one

    @property
    def standard_line(self) -> str | None:
        if self.line is not None:
            return self.line
        return self.name if self.name in STANDARD_LINES else None


@dataclass(frozen=True)
class Golden:
    """A case whose expected outputs come from outside the module's own oracle."""

    inputs: dict[str, Any]
    outputs: dict[str, list[float]]
    source: str  # where the numbers come from: a document, a person's hand sum, another tool
    kind: str  # one of INDEPENDENT_KINDS


@dataclass(frozen=True)
class Module:
    name: str
    version: str
    scope: dict[str, list[str]]  # {"in": [...], "out": [...]}
    inputs: tuple[Port, ...]
    outputs: tuple[Port, ...]
    oracle: Callable[[dict[str, Any]], dict[str, list[float]]]
    build: Callable[[BuildContext], None]
    checks: Callable[[BuildContext], dict[str, str]]
    example: dict[str, Any]
    golden: Golden
    notes: str = ""
    #: breaches of the FAST audit on calculation rows the module accepts on purpose: {"<rule code> <label prefix>": "reason"}, e.g. {"3.03-05 DSCR": "one IF guards a nil denominator"}
    fast_declared: dict[str, str] = field(default_factory=dict)

    @property
    def ports(self) -> tuple[Port, ...]:
        return self.inputs + self.outputs


@dataclass
class BuildContext:
    """What a module's formula half is given while it builds onto a Calcs sheet."""

    module: Module
    calcs: Any
    n: int
    sources: dict[str, str]  # input port -> Inputs ref or "Sheet!{col}row" pattern
    inputs: dict[str, Any]  # the input values being built for
    registry: dict = field(default_factory=dict)

    def source(self, port: str) -> str:
        """The `source` to give `Block.link` for an input port."""
        return self.sources[port]

    def values(self, port: str) -> list[float]:
        """The input port's values per period (a scalar is repeated), for `Block.link(values=)`."""
        v = self.inputs[port]
        return [float(x) for x in v] if isinstance(v, list | tuple) else [float(v)] * self.n

    def key(self, port: str) -> str:
        """The Calcs row key an output port's row must be registered under."""
        return f"{self.module.name}.{port}"

    def block(self, title: str):
        from .harness.fastblock import Block

        return Block(self.calcs, title, registry=self.registry)
