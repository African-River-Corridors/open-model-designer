# Golden answer: cash_sweep_percent

## Outputs
```python
sweep_amount = [150, 225, 0, 50]
debt_after_sweep = [750, 475, 600, 0]
cash_after_sweep = [50, 75, 100, 450]
```

## Working (sweep percent 0.75)
| Period | Cash avail | Debt before | Flag | 0.75 x cash | Amount = min(0.75 x cash, debt) | Sweep = flag x amount | Debt after | Cash after |
|---|---|---|---|---|---|---|---|---|
| 1 | 200 | 900 | 1 | 150 | 150 | 150 | 750 | 50 |
| 2 | 300 | 700 | 1 | 225 | 225 | 225 | 475 | 75 |
| 3 | 100 | 600 | 0 | 75 | 75 | 0 | 600 | 100 |
| 4 | 500 | 50 | 1 | 375 | 50 | 50 | 0 | 450 |

## Notes — ambiguity
- None in the stated rules. debt_before_sweep is a per-period input, not rolled forward from the prior
  period's debt_after_sweep (P2 debt before is 700, not 750). That is correct for a module that sits
  after the scheduled repayment; the roll-forward belongs to the debt module.

## Notes — coverage
- Good: the flag-0 branch (P3) and the debt cap (P4) both fire, each in a distinct period.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
