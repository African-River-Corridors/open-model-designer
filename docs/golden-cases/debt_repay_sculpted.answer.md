# Golden answer: debt_repay_sculpted

## Outputs
```python
interest = [36.0, 30.96, 24.1776, 15.548256]
debt_repayment = [84.0, 113.04, 143.8224, 176.451744]
debt_service = [120.0, 144.0, 168.0, 192.0]
debt_closing = [516.0, 402.96, 259.1376, 82.685856]
```

## Working (rate 0.06, opening 600, target DSCR 1.25)
| Period | Opening | Interest = 0.06 x opening | CFADS | CFADS / 1.25 | Principal = max(target - interest, 0), cap opening | Debt service | Closing |
|---|---|---|---|---|---|---|---|
| 1 | 600.0000 | 36.0000 | 150 | 120 | 84.0000 | 120 | 516.0000 |
| 2 | 516.0000 | 30.9600 | 180 | 144 | 113.0400 | 144 | 402.9600 |
| 3 | 402.9600 | 24.1776 | 210 | 168 | 143.8224 | 168 | 259.1376 |
| 4 | 259.1376 | 15.548256 | 240 | 192 | 176.451744 (< 259.14, cap not hit) | 192 | 82.685856 |
Check: DSCR = CFADS / service = 1.25 every period.

## Notes
- Rule is clear. The literal result leaves 82.69 unpaid at the end. In standard sculpting (Yescombe,
  Bodmer) the debt is SIZED to the PV of CFADS / DSCR at the loan rate, so it clears exactly. Here the
  debt is given (600) and is too big for these CFADS: PV of 120, 144, 168, 192 at 6% = 534.51, so a
  sculpted loan would be about 534.51, not 600. Not an error in the rule, but the module should show the
  residual, not hide it.
- Coverage gap: neither the max(., 0) floor nor the opening-balance cap fires in this case.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
