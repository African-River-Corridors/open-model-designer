"""T7: the toy module is accepted; one failing fixture per criterion turns its own criterion red."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.acceptance import AcceptanceError, assert_accepted, check_module
from omd.lines import STANDARD_LINES, dimension_of, valid_unit
from omd.module import Golden, Port
from omd.modules.levy import LEVY
from omd.modules.levy import checks as levy_checks
from omd.modules.levy import oracle as levy_oracle


# --- the module that passes ----------------------------------------------------------------------------
def test_the_toy_module_is_accepted_on_all_six_criteria():
    assert check_module(LEVY) == []
    assert_accepted(LEVY)


def test_the_ci_entry_point_accepts_it_and_rejects_a_bad_one(capsys, monkeypatch):
    assert acceptance.main(["omd.modules.levy:MODULE"]) == 0
    assert "accepted (criteria 1-6)" in capsys.readouterr().out
    assert acceptance.main(["nonsense"]) == 2


def test_about_twenty_standard_lines_each_with_a_dimension():
    assert len(STANDARD_LINES) == 20
    assert set(STANDARD_LINES.values()) == {"currency"}
    assert dimension_of("USD") == "currency" and dimension_of("ratio") == "ratio"
    assert (
        valid_unit("USD/tonne")
        and not valid_unit("")
        and not valid_unit("  ")
        and not valid_unit(None)
    )


# --- one failing fixture per criterion --------------------------------------------------------------------
def with_port(module, name, **changes):
    swap = lambda ps: tuple(replace(p, **changes) if p.name == name else p for p in ps)  # noqa: E731
    return replace(module, inputs=swap(module.inputs), outputs=swap(module.outputs))


def levy_checks_missing_gross(ctx):
    spec = levy_checks(ctx)
    return {"levy": spec["levy"]}  # the gross row is written but nothing checks it


def levy_checks_that_cannot_fire(ctx):
    c = ctx.calcs
    c.section("Checks")
    c.row("chk_dead", "  Check - always zero (USD)", lambda x: "=0", values=[0.0] * ctx.n)
    return {"dead": "Check - always zero"}


def levy_oracle_off_by_one(inputs):
    out = levy_oracle(inputs)
    out["tax_paid"] = [v + 1.0 for v in out["tax_paid"]]
    return out


def levy_build_with_if_row(ctx):
    """The toy build plus a calculation row that uses an IF where a flag row would do."""
    LEVY.build(ctx)
    c = ctx.calcs
    row = c.rows()[ctx.key("tax_paid")]
    c.row("capped", "  Capped levy (USD)", lambda x: f"=IF({x.col}{row}>1,1,{x.col}{row})",
          values=[0.0] * ctx.n)  # fmt: skip


def levy_build_with_constant_row(ctx):
    """The toy build plus a calculation row with a number written into its formula."""
    LEVY.build(ctx)
    c = ctx.calcs
    row = c.rows()[ctx.key("tax_paid")]
    c.row("scaled", "  Scaled levy (USD)", lambda x: f"={x.col}{row}*7.5", values=[0.0] * ctx.n)


def levy_oracle_extra_output(inputs):
    return {**levy_oracle(inputs), "stray": [0.0] * 4}


GOLD = LEVY.golden

FIXTURES = {
    # criterion 1: ports with units
    "1: a port with no unit": (
        "1",
        with_port(LEVY, "revenue", unit=""),
        "missing or malformed unit",
    ),
    "1: a unit that is not valid text": (
        "1",
        with_port(LEVY, "revenue", unit="$$"),
        "malformed unit",
    ),
    "1: a unit of the wrong dimension for its standard line": (
        "1",
        with_port(LEVY, "tax_paid", unit="ratio"),
        "standard line 'tax_paid' is currency",
    ),  # fmt: skip
    "1: a line name that is not a standard line": (
        "1",
        with_port(LEVY, "revenue", line="turnover"),
        "not a standard line name",
    ),  # fmt: skip
    "1: the same port name twice": (
        "1",
        replace(LEVY, inputs=LEVY.inputs + (Port("revenue", "USD"),)),
        "used twice",
    ),  # fmt: skip
    "1: no output ports": ("1", replace(LEVY, outputs=()), "no output ports"),
    # criterion 2: oracle and formula halves agree
    "2: the halves disagree": (
        "2",
        replace(LEVY, oracle=levy_oracle_off_by_one),
        "output 'tax_paid'",
    ),  # fmt: skip
    "2: the oracle returns an output with no port": (
        "2",
        replace(LEVY, oracle=levy_oracle_extra_output),
        "!= ports",
    ),  # fmt: skip
    # criterion 3: golden case from an independent source
    "3: the golden source is the module's own oracle": (
        "3",
        replace(LEVY, golden=replace(GOLD, kind="oracle")),
        "not independent",
    ),  # fmt: skip
    "3: no source named": ("3", replace(LEVY, golden=replace(GOLD, source="  ")), "no golden case"),
    "3: the golden numbers are wrong": (
        "3",
        replace(
            LEVY,
            golden=replace(
                GOLD, outputs={**GOLD.outputs, "tax_paid": [150.0, 320.0, 480.0, 640.0]}
            ),
        ),
        "disagrees with the golden case",
    ),  # fmt: skip
    "3: the golden case is just the worked example": (
        "3",
        replace(LEVY, golden=replace(GOLD, inputs=LEVY.example)),
        "must be a different case",
    ),  # fmt: skip
    "3: an output has no golden value": (
        "3",
        replace(LEVY, golden=replace(GOLD, outputs={"tax_paid": GOLD.outputs["tax_paid"]})),
        "every output port",
    ),  # fmt: skip
    # criterion 4: corruption audit
    "4: a written row no check catches": (
        "4",
        replace(LEVY, checks=levy_checks_missing_gross),
        "no check catches",
    ),  # fmt: skip
    "4: a check that cannot fire": (
        "4",
        replace(LEVY, checks=levy_checks_that_cannot_fire),
        "no check catches",
    ),  # fmt: skip
    "4: no checks at all": ("4", replace(LEVY, checks=lambda ctx: {}), "declares no checks"),
    # criterion 5: scope note
    "5: no scope note": ("5", replace(LEVY, scope={}), "non-empty list under 'in'"),
    "5: nothing said about what is out of scope": (
        "5",
        replace(LEVY, scope={"in": ["x"], "out": []}),
        "under 'out'",
    ),  # fmt: skip
    "5: a blank line is not a scope": (
        "5",
        replace(LEVY, scope={"in": [" "], "out": ["y"]}),
        "under 'in'",
    ),  # fmt: skip
    # criterion 6: the FAST audit of the worked-example book
    "6: a calculation row that uses an IF": (
        "6",
        replace(LEVY, build=levy_build_with_if_row),
        "3.03-05",
    ),  # fmt: skip
    "6: a calculation row with a number in its formula": (
        "6",
        replace(LEVY, build=levy_build_with_constant_row),
        "3.04-01",
    ),  # fmt: skip
    "6: a declaration that matches no finding": (
        "6",
        replace(LEVY, fast_declared={"3.03-05 Capped levy": "stale: the row it excused is gone"}),
        "matches no finding",
    ),  # fmt: skip
    "6: a declared breach with no reason": (
        "6",
        replace(LEVY, build=levy_build_with_if_row, fast_declared={"3.03-05 Capped levy": " "}),
        "needs '<rule code> <label prefix>' and a reason",
    ),  # fmt: skip
}


@pytest.mark.parametrize("name", list(FIXTURES))
def test_each_failing_fixture_turns_its_own_criterion_red(name):
    criterion, module, phrase = FIXTURES[name]
    with pytest.raises(AcceptanceError) as e:
        assert_accepted(module, {criterion})
    assert e.value.criteria == {criterion}  # the error names this criterion and no other
    assert phrase in str(e.value)
    assert f"criterion {criterion} " in str(e.value)


@pytest.mark.parametrize("criterion", ["1", "2", "3", "4", "5", "6"])
def test_the_passing_module_is_clean_on_that_criterion_alone(criterion):
    """The control for the fixtures above: the same criterion is green on the unbroken module."""
    assert check_module(LEVY, {criterion}) == []


def test_every_criterion_has_a_failing_fixture():
    assert {c for c, _m, _p in FIXTURES.values()} == set(acceptance.CRITERIA)


def test_a_breach_the_module_declares_with_a_reason_is_accepted():
    declared = replace(
        LEVY,
        build=levy_build_with_if_row,
        fast_declared={"3.03-05 Capped levy": "the cap is a rule of the toy, one IF reads best"},
    )
    assert check_module(declared, {"6"}) == []


def test_a_check_row_is_exempt_from_the_length_and_first_period_rules_only():
    def build_with_long_check(ctx):
        LEVY.build(ctx)
        c = ctx.calcs
        row = c.rows()[ctx.key("tax_paid")]
        long = "+".join(f"ABS({{col}}{row}-{{col}}{row})" for _ in range(8))
        c.row("chk_long", "  Check - a long one (USD)", lambda x: "=" + long.format(col=x.col),
              values=[0.0] * ctx.n)  # fmt: skip

    assert check_module(replace(LEVY, build=build_with_long_check), {"6"}) == []


def test_a_module_that_breaks_two_criteria_reports_both():
    bad = replace(with_port(LEVY, "revenue", unit=""), scope={})
    assert check_module(bad, {"1", "5"}) and {
        f.criterion for f in check_module(bad, {"1", "5"})
    } == {"1", "5"}


def test_a_formula_half_that_cannot_build_fails_instead_of_crashing():
    def broken(ctx):
        ctx.block("x").calc("y", "Y (USD)", "{ghost}*2")

    fails = check_module(replace(LEVY, build=broken), {"2"})
    assert [f.criterion for f in fails] == ["2"] and "did not build" in fails[0].message


def test_the_golden_case_runs_the_formulas_too():
    """Right numbers in the oracle are not enough: a formula half that is wrong only on the golden
    inputs is caught by the golden criterion."""
    from omd.modules import levy

    def build_wrong_on_gold(ctx):
        levy.build(ctx)
        if ctx.inputs["levy_rate"] == 0.2:
            ctx.calcs.ws[f"C{ctx.calcs.rows()[ctx.key('tax_paid')]}"] = "=1"

    fails = check_module(replace(LEVY, build=build_wrong_on_gold), {"2", "3"})
    assert {f.criterion for f in fails} == {"3"}
    assert isinstance(GOLD, Golden)


# --- review F1: four ways a module used to be accepted with a row nobody watches ---------------------
def levy_build_with(extra=None, baked=False):
    """The toy's formula half, optionally with an extra row, or with the rate baked in as a number."""
    from omd.modules import levy

    def build(ctx):
        if not baked:
            levy.build(ctx)
        else:
            b = ctx.block("Output levy")
            want = levy.oracle(ctx.inputs)
            b.link("rev", ctx.source("revenue"), "Revenue (USD)", values=ctx.values("revenue"))
            rate = repr(float(ctx.inputs["levy_rate"]))  # the Python number, not the input cell
            b.calc("levy", "Levy (USD)", "{rev}*" + rate, key=ctx.key("tax_paid"),
                   values=want["tax_paid"])  # fmt: skip
            b.link(
                "rev2",
                ctx.source("revenue"),
                "Revenue (USD), restated",
                values=ctx.values("revenue"),
            )
            b.link("levy2", ctx.key("tax_paid"), "Levy (USD), restated", values=want["tax_paid"])
            b.calc("gross", "Revenue incl. levy (USD)", "{rev2}+{levy2}", key=ctx.key("revenue_gross"),
                   values=want["revenue_gross"])  # fmt: skip
        if extra:
            extra(ctx)

    return build


def orphan_row(label):
    def add(ctx):
        b = ctx.block("Orphan")
        b.link("r", ctx.source("revenue"), "Revenue (USD)", values=ctx.values("revenue"))
        b.calc("orph", label, "{r}*2", values=[2 * v for v in ctx.values("revenue")])

    return add


def partial_period_checks(ctx):
    """Both checks read 0 in periods 2 and 3 and only re-derive in periods 1 and 4."""
    c = ctx.calcs
    rows = c.rows()
    rate, src = ctx.source("levy_rate"), ctx.source("revenue")
    lv, gr = rows[ctx.key("tax_paid")], rows[ctx.key("revenue_gross")]
    live = {"C", "F"}
    c.section("Checks")
    c.row("chk_levy", "  Check - levy re-derived (USD)",
          lambda x: f"={x.col}{lv}-{src.format(col=x.col)}*{rate}" if x.col in live else "=0",
          values=[0.0] * ctx.n)  # fmt: skip
    c.row("chk_gross", "  Check - gross re-derived (USD)",
          lambda x: f"={x.col}{gr}-{src.format(col=x.col)}*(1+{rate})" if x.col in live else "=0",
          values=[0.0] * ctx.n)  # fmt: skip
    return {"levy": "Check - levy re-derived", "gross": "Check - gross re-derived"}


F1_FIXTURES = {
    "a second row with a label already used": (
        "4",
        replace(LEVY, build=levy_build_with(orphan_row("Revenue (USD)"))),
        "no check catches",
    ),  # fmt: skip
    "a written row with a blank label": (
        "4",
        replace(LEVY, build=levy_build_with(orphan_row("   "))),
        "no label",
    ),  # fmt: skip
    "checks that watch only some periods": (
        "4",
        replace(LEVY, checks=partial_period_checks),
        "no check catches",
    ),  # fmt: skip
    "a rate baked into the formula as a number": (
        "2",
        replace(LEVY, build=levy_build_with(baked=True)),
        "does not follow input 'levy_rate'",
    ),  # fmt: skip
}


@pytest.mark.parametrize("name", list(F1_FIXTURES))
def test_a_module_with_an_unwatched_row_is_no_longer_accepted(name):
    criterion, module, phrase = F1_FIXTURES[name]
    with pytest.raises(AcceptanceError) as e:
        assert_accepted(module, {criterion})
    assert e.value.criteria == {criterion} and phrase in str(e.value)


def test_a_unique_label_orphan_was_already_caught_and_still_is():
    module = replace(LEVY, build=levy_build_with(orphan_row("Orphan (USD)")))
    assert {f.criterion for f in check_module(module, {"4"})} == {"4"}


def test_a_zero_cell_is_audited_not_skipped():
    """The perturbation is additive, so a zero is perturbed too. Revenue 0 in period 1 means the
    rate cell of period 1 cannot reach any output: that one cell is reported, and nothing else."""
    zero = replace(LEVY, example={"revenue": [0.0, 2000.0, 3000.0, 4000.0], "levy_rate": 0.125})
    fails = check_module(zero, {"4"})
    assert [f.message.split(":")[0] for f in fails] == ["row 'Levy rate (ratio)' period 1"]


def test_a_row_whose_effect_vanishes_in_the_example_is_reported():
    """With a rate of 0 a change to the revenue row cannot reach any output, so no check can see it:
    the example must be changed. Fail-closed."""
    flat = replace(LEVY, example={"revenue": LEVY.example["revenue"], "levy_rate": 0.0})
    fails = check_module(flat, {"4"})
    assert fails and {f.criterion for f in fails} == {"4"}


# --- re-review R1: the Open column is a written cell too ---------------------------------------------
def levy_with_unchecked_opening_balance(unchecked=True):
    """A roll-forward of the levy whose opening balance no check can see. Its step check reads each
    period against the cell before it, the Open cell for period 1, so a wrong opening value moves
    the balance and the check together. With `unchecked=False` the check also pins the opening."""
    from omd.modules import levy

    def build(ctx):
        levy.build(ctx)
        want = levy.oracle(ctx.inputs)["tax_paid"]
        run, bal = 100.0, []
        for v in want:
            run += v
            bal.append(run)
        ctx.calcs.roll(
            "bal", "  Balance (USD)", opening=100.0, add=[ctx.key("tax_paid")], values=bal
        )

    def checks(ctx):
        spec = levy_checks(ctx)
        c, lv = ctx.calcs, ctx.key("tax_paid")
        c.row(
            "chk_bal",
            "  Check - balance steps (USD)",
            lambda x: f"={x.here('bal')}-{x.prevref('bal')}-{x.here(lv)}",
            values=[0.0] * ctx.n,
        )
        if not unchecked:
            r = c.rows()["bal"]
            c.row(
                "chk_open",
                "  Check - opening balance (USD)",
                lambda x: f"=$B{r}-100",
                values=[0.0] * ctx.n,
            )
            return {**spec, "bal": "Check - balance steps", "open": "Check - opening balance"}
        return {**spec, "bal": "Check - balance steps"}

    return build, checks


def test_an_opening_balance_no_check_watches_is_not_accepted():
    build, checks = levy_with_unchecked_opening_balance(unchecked=True)
    module = replace(LEVY, build=build, checks=checks)
    with pytest.raises(AcceptanceError) as e:
        assert_accepted(module, {"4"})
    assert e.value.criteria == {"4"}
    assert "opening" in str(e.value) and "Balance (USD)" in str(e.value)
    assert all("period" not in f.message or "opening" in f.message for f in e.value.failures)


def test_the_same_roll_forward_is_accepted_once_a_check_pins_the_opening():
    build, checks = levy_with_unchecked_opening_balance(unchecked=False)
    assert check_module(replace(LEVY, build=build, checks=checks), {"4"}) == []


def test_every_module_is_in_exactly_one_acceptance_shard():
    from omd.acceptance import shard_names
    from omd.registry import discover

    names = list(discover("omd.modules"))
    dealt = [n for i in range(4) for n in shard_names(names, 4, i)]
    assert sorted(dealt) == sorted(names)


def test_a_shard_that_finds_no_modules_fails(capsys):
    from omd import acceptance

    assert acceptance.main(["--all", "omd.modules", "--shard", "99/100"]) == 1
    assert "found no modules" in capsys.readouterr().out
