# Golden answer: debt_repay_linear

## Outputs
```python
interest = [48, 36, 24, 12]
debt_repayment = [300, 300, 300, 0]
debt_service = [348, 336, 324, 12]
debt_closing = [900, 600, 300, 300]
```

## Working (rate 0.04, opening 1200, principal = 1200 / 4 = 300 when flagged)
| Period | Opening | Interest = 0.04 x opening | Flag | Principal = min(300, opening) | Debt service | Closing |
|---|---|---|---|---|---|---|
| 1 | 1200 | 48 | 1 | 300 | 348 | 900 |
| 2 | 900 | 36 | 1 | 300 | 336 | 600 |
| 3 | 600 | 24 | 1 | 300 | 324 | 300 |
| 4 | 300 | 12 | 0 | 0 | 12 | 300 |

## Notes — ambiguity
- repayment_periods = 4 but only 3 periods are flagged. The literal rule repays 300 x 3 = 900 and leaves
  300 outstanding at the end, with no balloon. Standard practice (Yescombe, Bodmer) sizes a straight-line
  tranche over the flagged repayment periods, so the loan clears. Under that reading (principal =
  1200 / 3 = 400):
  interest [48, 32, 16, 0], debt_repayment [400, 400, 400, 0], debt_service [448, 432, 416, 0],
  debt_closing [800, 400, 0, 0].
- Suggest the module either derives n from the flag count, or raises when n is not equal to the flag count.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
