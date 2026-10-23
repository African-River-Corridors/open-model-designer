# Golden answer: distribution_waterfall_2 (variant of OMD M20)

## Inputs (same rules as distribution_waterfall; 4 periods)
- distributable_cash = [0, -100, 1500, 500]
- equity_contribution = [1000, 0, 0, 100]
- hurdle_rate = 0.21        (one 0.5-year period accrues 10%)
- period_years = 0.5
- promote_share = 0.2
- opening_hurdle_balance = 0
- Rules: accrual = opening x ((1 + hurdle_rate)^period_years - 1); before paying = opening + accrual +
  contribution; tier 1 = min(max(cash, 0), before paying); closing = before paying - tier 1;
  residual = max(cash, 0) - tier 1; promote = promote_share x residual; investor = tier 1 + residual - promote.

## Outputs
```python
hurdle_accrual = [0, 100, 110, 0]
hurdle_balance_closing = [1000, 1100, 0, 0]
tier1_distribution = [0, 0, 1210, 100]
residual_cash = [0, 0, 290, 400]
sponsor_promote = [0, 0, 58, 80]
investor_distribution = [0, 0, 1442, 420]
```

## Working
| Period | Opening | Accrual (x 0.1) | Contribution | Before paying | Dist. cash | max(cash, 0) | Tier 1 | Closing | Residual | Promote | Investor |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 1000 | 1000 | 0 | 0 | 0 | 1000 | 0 | 0 | 0 |
| 2 | 1000 | 100 | 0 | 1100 | -100 | 0 | min(0, 1100) = 0 | 1100 | 0 - 0 = 0 | 0 | 0 |
| 3 | 1100 | 110 | 0 | 1210 | 1500 | 1500 | min(1500, 1210) = 1210 | 0 | 290 | 58 | 1210 + 290 - 58 = 1442 |
| 4 | 0 | 0 | 100 | 100 | 500 | 500 | min(500, 100) = 100 | 0 | 400 | 80 | 100 + 400 - 80 = 420 |

Checks: P3 investor + promote = 1442 + 58 = 1500; P4 420 + 80 = 500.
Floating point: P3 accrual computes as 110.0000000000001 (about 1e-13); exact value is 110.

## Notes — ambiguity
- P2: the -100 is floored to 0 and lost. It does not carry forward and does not raise the hurdle. This
  follows the literal rule. If the module instead treats negative cash as a deemed contribution, P2
  before-paying would be 1200, P3 accrual 120, P3 tier 1 1320, residual 180, promote 36, investor 1464.
- P4: a contribution after the hurdle is cleared re-opens the hurdle at 100 and is returned in full in
  the same period, before any split (see the same-period note in the main answer).

## Notes — coverage
- Fired: zero cash (P1); negative cash floored (P2); accrual on an unpaid, rolled-up balance (P2 to P3);
  hurdle crossed within a period (P3); accrual on a zero opening balance after clearance (P4);
  contribution after clearance (P4); positive residual and promote (P3, P4).
- With the main case, this covers every branch of the stated rules.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
