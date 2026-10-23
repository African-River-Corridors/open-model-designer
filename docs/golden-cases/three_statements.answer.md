# Golden answer: three_statements (OMD M22)

## Outputs
```python
ebitda = [400, 470, 550, 630]
ebit = [300, 370, 450, 530]
profit_before_tax = [240, 318, 406, 494]
net_income = [192, 254, 326, 398]
cash_from_operations = [300, 352, 424, 511]
cash_from_investing = [-200, -50, 0, 0]
cash_from_financing = [60, -90, -200, -260]
net_cash_flow = [160, 212, 224, 251]
cash_closing = [310, 522, 746, 997]
tax_payable_closing = [48, 56, 64, 72]
share_capital_closing = [400, 450, 450, 450]
retained_earnings_closing = [402, 596, 802, 1040]
total_assets = [1510, 1682, 1816, 1962]
total_liabilities_equity = [1510, 1682, 1816, 1962]
balance_difference = [0, 0, 0, 0]
```

## Working
Opening check: assets 150 + 1000 + 80 = 1230; L&E 600 + 20 + 400 + 210 = 1230.

### Income statement
| P | Revenue - opex = EBITDA | - dep = EBIT | - interest = PBT | - tax charge = NI |
|---|---|---|---|---|
| 1 | 800 - 400 = 400 | 400 - 100 = 300 | 300 - 60 = 240 | 240 - 48 = 192 |
| 2 | 900 - 430 = 470 | 370 | 370 - 52 = 318 | 318 - 64 = 254 |
| 3 | 1000 - 450 = 550 | 450 | 450 - 44 = 406 | 406 - 80 = 326 |
| 4 | 1100 - 470 = 630 | 530 | 530 - 36 = 494 | 494 - 96 = 398 |

### Cash flow
| P | CFO = NI + dep - WC mvt + tax charge - tax paid | CFI | CFF = draw - repay + equity - divs | NCF | Cash open -> close |
|---|---|---|---|---|---|
| 1 | 192 + 100 - 20 + 48 - 20 = 300 | -200 | 100 - 40 + 0 - 0 = 60 | 160 | 150 -> 310 |
| 2 | 254 + 100 - 10 + 64 - 56 = 352 | -50 | 0 - 80 + 50 - 60 = -90 | 212 | 310 -> 522 |
| 3 | 326 + 100 - 10 + 80 - 72 = 424 | 0 | 0 - 80 + 0 - 120 = -200 | 224 | 522 -> 746 |
| 4 | 398 + 100 + 5 + 96 - 88 = 511 | 0 | 0 - 100 + 0 - 160 = -260 | 251 | 746 -> 997 |

### Balance sheet
| P | Tax payable = open + charge - paid | Share cap | RE = open + NI - divs | TA = cash + NBV + WC | TLE = debt + tax + SC + RE | Diff |
|---|---|---|---|---|---|---|
| 1 | 20 + 48 - 20 = 48 | 400 | 210 + 192 - 0 = 402 | 310 + 1100 + 100 = 1510 | 660 + 48 + 400 + 402 = 1510 | 0 |
| 2 | 48 + 64 - 56 = 56 | 450 | 402 + 254 - 60 = 596 | 522 + 1050 + 110 = 1682 | 580 + 56 + 450 + 596 = 1682 | 0 |
| 3 | 56 + 80 - 72 = 64 | 450 | 596 + 326 - 120 = 802 | 746 + 950 + 120 = 1816 | 500 + 64 + 450 + 802 = 1816 | 0 |
| 4 | 64 + 96 - 88 = 72 | 450 | 802 + 398 - 160 = 1040 | 997 + 850 + 115 = 1962 | 400 + 72 + 450 + 1040 = 1962 | 0 |

### Supplied balances checked against their flows (all consistent)
- NBV: 1000 + 200 - 100 = 1100; + 50 - 100 = 1050; - 100 = 950; - 100 = 850.
- Working capital: 80 + 20 = 100; + 10 = 110; + 10 = 120; - 5 = 115.
- Debt: 600 + 100 - 40 = 660; - 80 = 580; - 80 = 500; - 100 = 400.

## Notes — ambiguity
- None that changes a number. Conventions assumed by the rules, all standard (Bodmer indirect method):
  interest is paid in cash in the period it is charged (no interest payable); a positive working-capital
  movement is an increase and so a cash outflow (matches the supplied WC balances); dividends need no
  distributable-reserves test (RE stays positive anyway).
- The balance check depends on the supplied NBV, WC and debt balances. The module does not roll them,
  so the check only proves the cash and equity side. A nonzero difference points at a supplied input or
  at cash/tax/RE.

## Notes — coverage
- Fired: WC release (negative movement, P4); tax paid below charge in every period (payable grows);
  equity contribution (P2); drawdown (P1); negative CFF (P2-P4).
- Not fired: a nonzero balance difference. That is the check's failing branch, so a module whose
  difference were hard-wired to 0 would pass. **Case marked weak.** See
  `three_statements_2.answer.md`, which corrupts one supplied balance so the check must fail.
- Also not fired (no branch in the rules, linear only): a loss-making period, negative net cash flow.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
