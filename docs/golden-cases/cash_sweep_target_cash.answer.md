# Golden answer: cash_sweep_target_cash

## Outputs
```python
sweep_amount = [100, 0, 300, 100]
debt_after_sweep = [700, 700, 350, 0]
cash_after_sweep = [200, 120, 200, 350]
```

## Working (target cash 200)
| Period | Cash avail | Debt before | Flag | Excess = max(cash - 200, 0) | Amount = min(excess, debt) | Sweep | Debt after | Cash after |
|---|---|---|---|---|---|---|---|---|
| 1 | 300 | 800 | 1 | 100 | 100 | 100 | 700 | 200 |
| 2 | 120 | 700 | 0 | max(-80, 0) = 0 | 0 | 0 | 700 | 120 |
| 3 | 500 | 650 | 1 | 300 | 300 | 300 | 350 | 200 |
| 4 | 450 | 100 | 1 | 250 | 100 | 100 | 0 | 350 |

## Notes — ambiguity
- None in the stated rules.

## Notes — coverage (weak)
- The zero floor and the flag-0 branch fire in the same period (P2). A module without the max(…, 0)
  floor gives the same output, because the flag zeroes the negative excess. Suggest P2 flag = 1
  (expect sweep 0, not -80), or a separate flagged period with cash below 200.
- The debt cap fires (P4).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
