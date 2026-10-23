"""M5: VAT account."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.vat_account import MODULE as M


def case(**kw):
    base = {
        "vat_input": [0.0] * 4,
        "vat_output": [0.0] * 4,
        "opening_vat_receivable": 0.0,
        "settle_share": 1.0,
        "write_off_at_end": 0.0,
    }
    return {**base, **kw}


def follows(inputs):
    return acceptance._compare(M, inputs, M.oracle(inputs), "2", "case") == []


def test_criterion_3_the_golden_case_comes_from_an_independent_hand_calculation():
    assert acceptance.check_module(M, {"3"}) == []
    assert (
        M.golden.kind == "hand-calculation"
        and "reviewer agent that did not see the code" in M.golden.source
    )
    # known weak spot: this case never fires the write-off or carries the payable forward.
    # vat_account_2.md asks for a second golden case that does; add it as a new test then.
    assert M.golden.outputs["vat_written_off"] == [0.0] * 4


def test_input_vat_builds_a_receivable_until_output_vat_offsets_it():
    inputs = case(vat_input=[100.0, 0.0, 0.0, 0.0], vat_output=[0.0, 60.0, 60.0, 0.0])
    out = M.oracle(inputs)
    assert out["vat_receivable_closing"] == [100.0, 40.0, 0.0, 0.0]
    assert out["vat_net_due"] == [0.0, 0.0, 20.0, 0.0]
    assert follows(inputs)


def test_the_receivable_is_written_off_in_the_last_period_only_when_switched_on():
    base = case(vat_input=[100.0, 0.0, 0.0, 0.0])
    off, on = M.oracle(base), M.oracle({**base, "write_off_at_end": 1.0})
    assert off["vat_written_off"] == [0.0] * 4 and off["vat_receivable_closing"][3] == 100.0
    assert on["vat_written_off"] == [0.0, 0.0, 0.0, 100.0]
    assert on["vat_receivable_closing"][3] == 0.0
    assert follows({**base, "write_off_at_end": 1.0})


def test_net_vat_is_paid_with_a_lag():
    inputs = case(vat_output=[100.0, 0.0, 0.0, 0.0], settle_share=0.25)
    out = M.oracle(inputs)
    assert out["vat_paid"] == [25.0, 75.0, 0.0, 0.0]
    assert out["vat_payable_closing"] == [75.0, 0.0, 0.0, 0.0]
    assert follows(inputs)


def test_an_opening_receivable_is_offset_first():
    inputs = case(vat_output=[30.0, 0.0, 0.0, 0.0], opening_vat_receivable=50.0)
    out = M.oracle(inputs)
    assert out["vat_offset"][0] == 30.0 and out["vat_receivable_closing"][0] == 20.0
    assert follows(inputs)


def test_both_balances_reconcile():
    inputs = case(
        vat_input=[40.0, 10.0, 0.0, 5.0], vat_output=[0.0, 70.0, 20.0, 9.0], settle_share=0.3
    )
    out = M.oracle(inputs)
    recv = pay = 0.0
    for i in range(4):
        recv += inputs["vat_input"][i] - out["vat_offset"][i] - out["vat_written_off"][i]
        pay += out["vat_net_due"][i] - out["vat_paid"][i]
        assert out["vat_receivable_closing"][i] == pytest.approx(recv)
        assert out["vat_payable_closing"][i] == pytest.approx(pay)


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def no_offset(inputs):
        return M.oracle({**inputs, "vat_input": [0.0] * 4})

    assert "2" in {
        f.criterion for f in acceptance.check_module(replace(M, oracle=no_offset), {"2"})
    }


def test_negative_control_without_checks_fails_criterion_4():
    bad = replace(M, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(bad, {"4"})}


# second golden case (independent hand calculation by a reviewer agent that did not see the code, 2026-10-23;
# working in docs/golden-cases/vat_account_2.answer.md): fires the write-off, and carries a payable
CASE_A = {
    "vat_input": [200.0, 0.0, 100.0, 50.0],
    "vat_output": [50.0, 150.0, 100.0, 20.0],
    "opening_vat_receivable": 30.0,
    "settle_share": 0.6,
    "write_off_at_end": 1.0,
}
OUT_A = {
    "vat_offset": [50, 150, 100, 20], "vat_net_due": [0, 0, 0, 0], "vat_paid": [0, 0, 0, 0],
    "vat_payable_closing": [0, 0, 0, 0], "vat_written_off": [0, 0, 0, 60],
    "vat_receivable_closing": [180, 30, 30, 0],
}  # fmt: skip
CASE_B = {
    "vat_input": [0.0] * 4,
    "vat_output": [100.0, 40.0, 0.0, 0.0],
    "opening_vat_receivable": 0.0,
    "settle_share": 0.6,
    "write_off_at_end": 1.0,
}
OUT_B = {
    "vat_offset": [0, 0, 0, 0], "vat_net_due": [100, 40, 0, 0], "vat_paid": [60, 64, 16, 0],
    "vat_payable_closing": [40, 16, 0, 0], "vat_written_off": [0, 0, 0, 0],
    "vat_receivable_closing": [0, 0, 0, 0],
}  # fmt: skip


@pytest.mark.parametrize(
    "inputs,want", [(CASE_A, OUT_A), (CASE_B, OUT_B)], ids=["write-off fires", "payable carries"]
)
def test_the_second_golden_case_agrees_with_the_oracle_and_the_formulas(inputs, want):
    got = M.oracle(inputs)
    for k, v in want.items():
        assert got[k] == pytest.approx([float(x) for x in v]), k
    assert (
        acceptance._compare(
            M, inputs, {k: [float(x) for x in v] for k, v in want.items()}, "3", "golden 2"
        )
        == []
    )
