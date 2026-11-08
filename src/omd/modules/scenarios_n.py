"""Scenarios and sensitivities for any horizon: the `scenarios` module's logic, with the number of periods set by
the factory instead of fixed at 4 (OMD issue 14). `scenarios` is released and write-once, so this is a new module.

Scenarios and sensitivities: named scenario sets, a one-at-a-time table, a tornado ranking
and breakeven, with one live point reconciled to the table.

The module is configured, not coded: `make_scenarios_n(drivers, scenarios, periods=n)` builds it for any named drivers and
scenarios. `MODULE` is the default (three drivers, three scenarios).

    live multiplier of a driver = the multiplier of the selected scenario            (feed this to the model)
    swing of a driver           = |result with the driver up - result with it down|   (others at base)
    tornado rank                = 1 for the largest swing; equal swings share a rank
    breakeven multiplier        = the multiplier of the driver that makes the result nil, on the straight line
                                  through the up and down results (0 when the driver has no swing; `no_sensitivity` is then 1)
    live result in the table    = the table's result for the selected scenario
    reconciliation              = the live model's result - the table's result for the selected scenario

The oracle runs per point: `run_points` calls a model's oracle once for every scenario and for each driver up and
down, and gives the module its inputs. The live model's own result for the selected scenario comes back in on
`live_result`; the reconciliation row and its check read non-zero if it disagrees with the table.
"""

from __future__ import annotations

from dataclasses import replace

from ..module import BuildContext, Module, Port
from ._plan_module import build_plan, plan_checks
from .scenarios import DEFAULT_DRIVERS, DEFAULT_SCENARIOS, EXAMPLE, SCENARIOS, run_points

__all__ = ["make_scenarios_n", "run_points", "MODULE"]


def make_scenarios_n(
    drivers=DEFAULT_DRIVERS,
    scenarios=DEFAULT_SCENARIOS,
    *,
    periods: int = 4,
    example=None,
    golden=None,
    name: str = "scenarios_n",
) -> Module:
    """The module for `periods` periods. Every output is one value per period, the same across the row."""
    drivers, scenarios = tuple(drivers), tuple(scenarios)
    if periods < 1:
        raise ValueError("scenarios_n needs at least one period")
    S, D = len(scenarios), len(drivers)
    assert S >= 2 and D >= 2, "a scenario set and a tornado need at least two of each"
    INPUTS = (
        Port("scenario_selector", "count", "scalar"),
        Port("sensitivity_step", "ratio", "scalar"),
        Port("base_result", "USD", "scalar"),
        Port("live_result", "USD", "scalar"),
        *(Port(f"multiplier__{d}__{s}", "ratio", "scalar") for d in drivers for s in scenarios),
        *(Port(f"scenario_result__{s}", "USD", "scalar") for s in scenarios),
        *(Port(f"result_{k}__{d}", "USD", "scalar") for d in drivers for k in ("down", "up")),
    )
    OUTPUTS = (
        *(Port(f"live_multiplier__{d}", "ratio", "series") for d in drivers),
        Port("live_scenario_result", "USD", "series"),
        Port("live_reconciliation", "USD", "series"),
        *(Port(f"swing__{d}", "USD", "series") for d in drivers),
        *(Port(f"tornado_rank__{d}", "count", "series") for d in drivers),
        *(Port(f"breakeven_multiplier__{d}", "ratio", "series") for d in drivers),
        *(Port(f"no_sensitivity__{d}", "count", "series") for d in drivers),
    )
    T = "Scenarios and sensitivities"
    KEYED: dict[str, str] = {}
    PLAN: list[tuple[str, str, str, str]] = []
    for i, d in enumerate(drivers):
        PLAN.append(("link", f"sel_m{i}", "Selected scenario (count)", "scenario_selector"))
        for j, s in enumerate(scenarios):
            PLAN.append(
                ("link", f"m_{i}_{j}", f"Multiplier - {d} in {s} (ratio)", f"multiplier__{d}__{s}")
            )
        PLAN.append(("calc", f"live{i}", f"Live multiplier - {d} (ratio)",
                     "CHOOSE({" + f"sel_m{i}" + "}," + ",".join("{" + f"m_{i}_{j}" + "}" for j in range(S)) + ")"))  # fmt: skip
        KEYED[f"live{i}"] = f"live_multiplier__{d}"
    PLAN.append(("link", "sel_r", "Selected scenario (count)", "scenario_selector"))
    for j, s in enumerate(scenarios):
        PLAN.append(("link", f"r_{j}", f"Result - scenario {s} (USD)", f"scenario_result__{s}"))
    PLAN.append(("calc", "table", "Table result for the selected scenario (USD)",
                 "CHOOSE({sel_r}," + ",".join("{" + f"r_{j}" + "}" for j in range(S)) + ")"))  # fmt: skip
    KEYED["table"] = "live_scenario_result"
    PLAN += [
        ("link", "live", "Result of the live model (USD)", "live_result"),
        ("relink", "table2", "Table result for the selected scenario (USD)", "table"),
        ("calc", "recon", "Live model less the table (USD)", "{live}-{table2}"),
    ]
    KEYED["recon"] = "live_reconciliation"
    for i, d in enumerate(drivers):
        PLAN += [
            ("link", f"up{i}", f"Result - {d} up (USD)", f"result_up__{d}"),
            ("link", f"dn{i}", f"Result - {d} down (USD)", f"result_down__{d}"),
            (
                "calc",
                f"swing{i}",
                f"Swing - {d} (USD)",
                "ABS({" + f"up{i}" + "}-{" + f"dn{i}" + "})",
            ),
        ]
        KEYED[f"swing{i}"] = f"swing__{d}"
    for i, d in enumerate(drivers):
        others = [k for k in range(D) if k != i]
        PLAN.append(("relink", f"sw_self{i}", f"Swing - {d} (USD)", f"swing{i}"))
        for k in others:
            PLAN.append(("relink", f"sw_{i}_{k}", f"Swing - {drivers[k]} (USD)", f"swing{k}"))
        PLAN.append(("calc", f"rank{i}", f"Tornado rank - {d} (count)",
                     "1+" + "+".join("({" + f"sw_{i}_{k}" + "}>{" + f"sw_self{i}" + "})" for k in others)))  # fmt: skip
        KEYED[f"rank{i}"] = f"tornado_rank__{d}"
    for i, d in enumerate(drivers):
        PLAN += [
            ("link", f"base{i}", "Result at base (USD)", "base_result"),
            ("link", f"step{i}", "Sensitivity step (ratio)", "sensitivity_step"),
            ("calc", f"step2{i}", "Distance between the up and down points (ratio)", "2*{" + f"step{i}" + "}"),
            ("link", f"upb{i}", f"Result - {d} up (USD)", f"result_up__{d}"),
            ("link", f"dnb{i}", f"Result - {d} down (USD)", f"result_down__{d}"),
            ("calc", f"slope{i}", f"Slope - {d} (USD per unit of multiplier)", "({" + f"upb{i}" + "}-{" + f"dnb{i}" + "})/{" + f"step2{i}" + "}"),
            ("relink", f"swn{i}", f"Swing - {d} (USD)", f"swing{i}"),
            ("calc", f"nosens{i}", f"No sensitivity - {d}: 1 where the swing is nil, so a breakeven of 0 is not read as real (flag)", "({" + f"swn{i}" + "}=0)*1"),
            ("relink", f"slope2_{i}", f"Slope - {d} (USD per unit of multiplier)", f"slope{i}"),
            ("relink", f"ns2_{i}", f"No sensitivity - {d} (flag)", f"nosens{i}"),
            ("calc", f"safe{i}", f"Slope, made safe to divide by where there is no swing - {d} (USD per unit of multiplier)", "{" + f"slope2_{i}" + "}+{" + f"ns2_{i}" + "}"),
            ("link", f"baseb{i}", "Result at base (USD)", "base_result"),
            ("relink", f"ns3_{i}", f"No sensitivity - {d} (flag)", f"nosens{i}"),
            ("calc", f"be{i}", f"Breakeven multiplier - {d} (ratio)", "(1-{" + f"ns3_{i}" + "})*(1-{" + f"baseb{i}" + "}/{" + f"safe{i}" + "})"),
        ]  # fmt: skip
        KEYED[f"be{i}"] = f"breakeven_multiplier__{d}"
        KEYED[f"nosens{i}"] = f"no_sensitivity__{d}"

    def _run(inp):
        sel = int(float(inp["scenario_selector"]))
        step, base = float(inp["sensitivity_step"]), float(inp["base_result"])
        V: dict[str, float] = {}
        for i, d in enumerate(drivers):
            ms = [float(inp[f"multiplier__{d}__{s}"]) for s in scenarios]
            V[f"sel_m{i}"] = float(sel)
            for j, m in enumerate(ms):
                V[f"m_{i}_{j}"] = m
            V[f"live{i}"] = ms[sel - 1]
        rs = [float(inp[f"scenario_result__{s}"]) for s in scenarios]
        V["sel_r"] = float(sel)
        for j, r in enumerate(rs):
            V[f"r_{j}"] = r
        V["table"], V["table2"] = rs[sel - 1], rs[sel - 1]
        V["live"] = float(inp["live_result"])
        V["recon"] = V["live"] - V["table"]
        for i, d in enumerate(drivers):
            up, dn = float(inp[f"result_up__{d}"]), float(inp[f"result_down__{d}"])
            V[f"up{i}"], V[f"dn{i}"], V[f"swing{i}"] = up, dn, abs(up - dn)
        for i in range(D):
            V[f"sw_self{i}"] = V[f"swing{i}"]
            for k in range(D):
                if k != i:
                    V[f"sw_{i}_{k}"] = V[f"swing{k}"]
            V[f"rank{i}"] = 1.0 + sum(
                1.0 for k in range(D) if k != i and V[f"swing{k}"] > V[f"swing{i}"]
            )
        for i in range(D):
            up, dn = V[f"up{i}"], V[f"dn{i}"]
            slope = (up - dn) / (2 * step)
            V[f"base{i}"], V[f"step{i}"], V[f"step2{i}"], V[f"upb{i}"], V[f"dnb{i}"] = (
                base,
                step,
                2 * step,
                up,
                dn,
            )
            ns = 1.0 if V[f"swing{i}"] == 0 else 0.0
            V[f"slope{i}"], V[f"baseb{i}"] = slope, base
            V[f"swn{i}"], V[f"nosens{i}"] = V[f"swing{i}"], ns
            V[f"slope2_{i}"], V[f"ns2_{i}"], V[f"ns3_{i}"] = slope, ns, ns
            V[f"safe{i}"] = slope + ns
            V[f"be{i}"] = (1 - ns) * (1 - base / (slope + ns))
        return V

    def oracle(inp: dict) -> dict[str, list[float]]:
        V = _run(inp)
        return {port: [V[k]] * periods for k, port in KEYED.items()}

    def _series(inp):
        V = _run(inp)
        return {k: [v] * periods for k, v in V.items()}

    def build(ctx: BuildContext) -> None:
        if ctx.n != periods:
            raise ValueError(f"{name} was made for {periods} periods; the workbook has {ctx.n}")
        build_plan(ctx, T, PLAN, _series(ctx.inputs), KEYED, {})

    def checks(ctx: BuildContext) -> dict[str, str]:
        c = ctx.calcs
        r = c.rows()
        src = {p.name: ctx.source(p.name) for p in INPUTS}
        K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
        zero = [0.0] * ctx.n
        absum = lambda parts: "=" + "+".join(f"ABS({p})" for p in parts)  # noqa: E731

        def choose(names):
            return (
                "CHOOSE(" + src["scenario_selector"] + "," + ",".join(src[n] for n in names) + ")"
            )

        def rank(x, i):
            others = [k for k in range(D) if k != i]
            return "1+" + "+".join(
                f"({K(f'swing__{drivers[k]}', x)}>{K(f'swing__{drivers[i]}', x)})" for k in others
            )

        c.section("Checks")
        c.row("chk_live", "  Check - live multipliers and the table result re-derived from the ports (USD)",
              lambda x: absum([K(f"live_multiplier__{d}", x) + "-" + choose([f"multiplier__{d}__{s}" for s in scenarios]) for d in drivers]
                              + [K("live_scenario_result", x) + "-" + choose([f"scenario_result__{s}" for s in scenarios]),
                                 K("live_reconciliation", x) + f"-({src['live_result']}-{choose([f'scenario_result__{s}' for s in scenarios])})"]),
              values=zero)  # fmt: skip
        c.row("chk_tornado", "  Check - swings and ranks re-derived from the ports (USD)",
              lambda x: absum([K(f"swing__{d}", x) + f"-ABS({src[f'result_up__{d}']}-{src[f'result_down__{d}']})" for d in drivers]
                              + [K(f"tornado_rank__{drivers[i]}", x) + "-(" + rank(x, i) + ")" for i in range(D)]),
              values=zero)  # fmt: skip
        c.row("chk_breakeven", "  Check - the result is nil at each breakeven multiplier on the straight line (USD)",
              lambda x: absum([f"({K(f'swing__{d}', x)}>0)*({src['base_result']}+({src[f'result_up__{d}']}-{src[f'result_down__{d}']})"
                               f"/(2*{src['sensitivity_step']})*({K(f'breakeven_multiplier__{d}', x)}-1))"
                               f"+({K(f'swing__{d}', x)}=0)*{K(f'breakeven_multiplier__{d}', x)}" for d in drivers]),
              values=zero)  # fmt: skip
        c.row("chk_nosens", "  Check - the no-sensitivity flags re-derived from the swings (count)",
              lambda x: absum([K(f"no_sensitivity__{d}", x) + f"-({src[f'result_up__{d}']}={src[f'result_down__{d}']})*1" for d in drivers]),
              values=zero)  # fmt: skip
        c.row("chk_reconciled", "  Check - the live model agrees with the table for the selected scenario (USD)",
              lambda x: f"=ABS({K('live_reconciliation', x)})", values=zero)  # fmt: skip
        label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: "0")
        return {
            "live": "Check - live multipliers and the table result re-derived from the ports",
            "tornado": "Check - swings and ranks re-derived from the ports",
            "breakeven": "Check - the result is nil at each breakeven multiplier on the straight line",
            "nosens": "Check - the no-sensitivity flags re-derived from the swings",
            "reconciled": "Check - the live model agrees with the table for the selected scenario",
            "rows": label,
        }

    return Module(
        name=name,
        version="0.1.0",
        scope={
            "in": [
                "Named scenario sets: each scenario gives a multiplier for every driver; one is selected as live",
                "A one-at-a-time table: each driver up and down by a step with the others at base, as results",
                "A tornado ranking by swing, and breakeven multipliers on the straight line through the up and down results, with a flag where a driver has no swing (its breakeven of 0 is then not a real one)",
                "The oracle run per point (`run_points`), and one live point reconciled to the table by a check",
            ],
            "out": [
                "Running the live model for every point inside the workbook (the table holds oracle results, not live formulas)",
                "Data tables, Monte Carlo and probability-weighted results",
                "Breakeven on a curved response (the line through two points is exact only for a linear model)",
                "Two-way sensitivities and the scenario definitions themselves (they are project data)",
            ],
        },
        inputs=INPUTS,
        outputs=OUTPUTS,
        oracle=oracle,
        build=build,
        checks=checks,
        example=example,
        golden=golden,
    )


SCENARIOS_N = make_scenarios_n(
    periods=4,
    example=EXAMPLE,
    golden=replace(
        SCENARIOS.golden,
        source="The scenarios module's golden case, reused: scenarios_n carries the same logic and only the horizon "
        "is a parameter. Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); "
        "working in docs/golden-cases/scenarios_3.answer.md",
    ),
)
MODULE = SCENARIOS_N
