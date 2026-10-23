# Golden answer: cash_sweep_target_leverage_3

## Inputs (cash_sweep_target_leverage_2 with period 2's flag set to 0; same rules)
- cash_available_for_sweep = [400, 100, 600, 600]
- debt_before_sweep = [1000, 900, 800, 500]
- ebitda = [300, 300, 320, 340]
- sweep_flag = [1, 0, 1, 1]       # period 2: flag off where the sweep would otherwise be 100
- target_leverage = 2.5
- amount = min(max(debt before - target leverage x EBITDA, 0), cash); sweep = flag x amount;
  debt after = debt before - sweep; cash after = cash - sweep

## Outputs
```python
sweep_amount = [250, 0, 0, 0]
debt_after_sweep = [750, 900, 800, 500]
cash_after_sweep = [150, 100, 600, 600]
```

## Working
| Period | Cash | Debt before | EBITDA | 2.5 x EBITDA | Excess = max(debt - 2.5 x EBITDA, 0) | Amount = min(excess, cash) | Flag | Sweep | Debt after | Cash after |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 400 | 1000 | 300 | 750 | 250 | 250 | 1 | 250 | 750 | 150 |
| 2 | 100 | 900 | 300 | 750 | 150 | min(150, 100) = 100 | 0 | 0 | 900 | 100 |
| 3 | 600 | 800 | 320 | 800 | 0 | 0 | 1 | 0 | 800 | 600 |
| 4 | 600 | 500 | 340 | 850 | max(-350, 0) = 0 | 0 | 1 | 0 | 500 | 600 |

## Flag check — confirmed, the flag changes the output
A module that ignored the flag would sweep 100 in P2 (debt after 800, cash after 0). The correct
result is 0 (debt 900, cash 100).

## Why period 2
Only P1 and P2 have a positive amount. P1 is the only clean test of the excess-debt cap below cash, so
I kept it flagged. Turning P2 off costs the cash-cap test in this case.

## Notes — ambiguity
- None in the stated rules.

## Notes — coverage
- Fired: excess-debt cap below cash (P1); flag 0 on a positive amount (P2); excess exactly 0 (P3);
  zero floor in a flagged period (P4).
- Not fired here: the cash cap in a flagged period. It is still covered by case 1 (P2: excess 150,
  cash 100, flag 1, sweep 100), so cases 1 and 3 together cover every branch. To cover all in one
  case, add a fifth period, e.g. cash 100, debt 900, EBITDA 300, flag 1 (expect sweep 100).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
