# Golden answer: cash_sweep_target_leverage

## Outputs
```python
sweep_amount = [250, 100, 0, 0]
debt_after_sweep = [750, 800, 800, 500]
cash_after_sweep = [0, 0, 600, 600]
```

## Working (target leverage 2.5)
| Period | Cash avail | Debt before | EBITDA | 2.5 x EBITDA | Excess debt = max(debt - 2.5 x EBITDA, 0) | Amount = min(excess, cash) | Flag | Sweep | Debt after | Cash after |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 250 | 1000 | 300 | 750 | 250 | min(250, 250) = 250 | 1 | 250 | 750 | 0 |
| 2 | 100 | 900 | 300 | 750 | 150 | min(150, 100) = 100 | 1 | 100 | 800 | 0 |
| 3 | 600 | 800 | 320 | 800 | 0 | 0 | 1 | 0 | 800 | 600 |
| 4 | 600 | 500 | 340 | 850 | max(-350, 0) = 0 | 0 | 0 | 0 | 500 | 600 |

## Notes — ambiguity
- None in the stated rules. Practice note: the leverage test usually uses LTM EBITDA; here EBITDA is a
  per-period input, so that is the caller's choice.

## Notes — coverage (weak)
- The zero floor never bites in a flagged period. P3 excess is exactly 0; P4 excess is negative but the
  flag is 0. A module without the max(…, 0) floor would pass. Suggest P4 flag = 1 (expect sweep 0, not -350).
- P1 is a tie (excess 250 = cash 250), so it cannot tell which cap binds. P2 does test the cash cap.
- The debt-excess side never binds below cash except at the tie, so "excess < cash" is not tested cleanly.
  Suggest P1 cash = 400 (expect sweep 250, cash after 150).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
