# Golden answer: cash_sweep_target_cash_2

## Outputs
```python
sweep_amount = [100, 0, 300, 0]
debt_after_sweep = [700, 700, 350, 100]
cash_after_sweep = [200, 120, 200, 450]
```

## Working (target cash 200)
| Period | Cash avail | Debt before | Flag | Excess = max(cash - 200, 0) | Amount = min(excess, debt) | Sweep = flag x amount | Debt after | Cash after |
|---|---|---|---|---|---|---|---|---|
| 1 | 300 | 800 | 1 | 100 | 100 | 100 | 700 | 200 |
| 2 | 120 | 700 | 1 | max(-80, 0) = 0 | 0 | 0 | 700 | 120 |
| 3 | 500 | 650 | 1 | 300 | 300 | 300 | 350 | 200 |
| 4 | 450 | 100 | 0 | 250 | min(250, 100) = 100 | 0 | 100 | 450 |

## Notes — ambiguity
- None in the stated rules. debt_before_sweep is a per-period input, not chained from the prior
  period's debt after (P3 650 is not P2's 700; P4 100 is not P3's 350). Fine for a unit case.

## Notes — coverage (still weak, one branch)
- Fixed: the zero floor now fires alone in a flagged period (P2: a module without the floor gives
  -80, debt 780, cash 200). The flag-0 branch now zeroes a positive amount (P4: ignoring the flag gives 100).
- Lost: the debt cap no longer fires in a flagged period. Its only case (P4) is now flag 0, so
  min(excess, debt) vs plain excess is untested here (both give sweep 0). Case 1 covers it, so the two
  cases together cover every branch, but this case alone does not.
- Suggested fix: P1 debt_before_sweep = 50 (expect sweep 50, debt after 0, cash after 250).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
