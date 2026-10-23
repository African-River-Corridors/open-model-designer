"""Wiring rows for a template: a few series that join one module's outputs to the next module's inputs.

A port wires to one row, so a feed such as "profit before tax" (revenue less cost, depreciation and interest) needs a
row of its own. `glue` builds a module whose outputs are such rows. Each output is a short expression over the glue's
inputs and its earlier outputs (names, `+ - *` and brackets, no numbers); the module re-links what each row uses, keeps
every calculation to four operators, and re-derives every row in its checks, as any plan module does.
"""

from __future__ import annotations

import re

from ..module import BuildContext, Golden, Module, Port
from ..modules._plan_module import build_plan, plan_checks

NAME = re.compile(r"[a-z_][a-z_0-9]*")


def _pretty(name: str) -> str:
    return name.replace("_", " ").capitalize()


def glue(
    name: str, inputs: dict[str, str], outputs: list[tuple[str, str]], example: dict
) -> Module:
    """`inputs`: name -> unit (a unit ending in ":scalar" is a scalar port). `outputs`: (name, expression) in order. `example`: the input series for the oracle."""
    scalars = {n for n, u in inputs.items() if u.endswith(":scalar")}
    inputs = {n: u.removesuffix(":scalar") for n, u in inputs.items()}
    in_ports = tuple(Port(n, u, "scalar" if n in scalars else "series") for n, u in inputs.items())
    out_ports = tuple(Port(n, "USD", "series") for n, _e in outputs)
    done: list[str] = []
    plan: list[tuple[str, str, str, str]] = []
    exprs: dict[str, str] = {}
    for out, expr in outputs:
        refs = []
        for ref in NAME.findall(expr):
            if ref not in refs:
                refs.append(ref)
        template = expr
        for ref in refs:
            row = f"{out}__{ref}"
            if ref in inputs:
                plan.append(("link", row, f"{_pretty(ref)} ({inputs[ref]})", ref))
            else:
                assert ref in done, f"{name}.{out}: {ref} is neither an input nor an earlier output"
                plan.append(("relink", row, f"{_pretty(ref)} (USD)", ref))
            template = re.sub(rf"\b{ref}\b", "{" + row + "}", template)
        plan.append(("calc", out, f"{_pretty(out)} (USD)", template))
        exprs[out] = template
        done.append(out)
    keyed = {out: out for out, _e in outputs}
    title = name.replace("_", " ").capitalize()

    def run(values: dict) -> dict[str, list[float]]:
        n = max(len(v) for v in values.values() if isinstance(v, list | tuple))
        V: dict[str, list[float]] = {row: [] for _k, row, _l, _s in plan}
        for i in range(n):
            cell: dict[str, float] = {}
            for kind, row, _l, spec in plan:
                if kind == "link":
                    cell[row] = float(values[spec] if spec in scalars else values[spec][i])
                elif kind == "relink":
                    cell[row] = cell[spec]
                else:
                    cell[row] = eval(
                        re.sub(r"\{(\w+)\}", lambda m, cell=cell: repr(cell[m.group(1)]), spec)
                    )  # noqa: S307
                V[row].append(cell[row])
        return V

    def oracle(values: dict) -> dict[str, list[float]]:
        V = run(values)
        return {out: V[out] for out, _e in outputs}

    def build(ctx: BuildContext) -> None:
        build_plan(ctx, title, plan, run(ctx.inputs), {row: out for row, out in keyed.items()}, {})

    def checks(ctx: BuildContext) -> dict[str, str]:
        ctx.calcs.section("Checks")
        return {"rows": plan_checks(ctx, title, plan, keyed, lambda port, x: "0")}

    outs = oracle(example)
    return Module(
        name=name, version="0.1.0",
        scope={"in": ["Series that join modules in a template"], "out": ["Anything a module of the library already does"]},
        inputs=in_ports, outputs=out_ports, oracle=oracle, build=build, checks=checks, example=example,
        golden=Golden(inputs=example, outputs=outs, source="template wiring: not a library module", kind="self"),
    )  # fmt: skip
