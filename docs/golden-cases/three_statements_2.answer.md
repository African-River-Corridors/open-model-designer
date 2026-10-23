# Golden answer: three_statements_2 (variant of OMD M22 — the balance check must fail)

## Inputs (three_statements with two supplied balances deliberately mis-stated; same rules)
- opening_cash = 150, opening_fixed_assets = 1000, opening_working_capital = 80, opening_debt = 600,
  opening_tax_payable = 20, opening_share_capital = 400, opening_retained_earnings = 210
- revenue = [800, 900, 1000, 1100]
- operating_cost = [400, 430, 450, 470]
- depreciation = [100, 100, 100, 100]
- interest = [60, 52, 44, 36]
- tax_charge = [48, 64, 80, 96]
- tax_paid = [20, 56, 72, 88]
- capital_additions = [200, 50, 0, 0]
- working_capital_movement = [20, 10, 10, -5]
- debt_drawdown = [100, 0, 0, 0]
- debt_repayment = [40, 80, 80, 100]
- equity_contribution = [0, 50, 0, 0]
- dividends = [0, 60, 120, 160]
- fa_nbv_closing = [1100, 1050, 960, 850]     # P3 mis-stated: flows give 950
- working_capital = [100, 110, 120, 115]
- debt_closing = [660, 590, 500, 400]         # P2 mis-stated: flows give 580

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
total_assets = [1510, 1682, 1826, 1962]
total_liabilities_equity = [1510, 1692, 1816, 1962]
balance_difference = [0, -10, 10, 0]
```

## Working
Income statement, cash flow, tax payable, share capital and retained earnings do not use the three
supplied balances, so they equal three_statements.answer.md exactly (see its tables).

| P | TA = cash + NBV + WC | TLE = debt + tax + SC + RE | Diff |
|---|---|---|---|
| 1 | 310 + 1100 + 100 = 1510 | 660 + 48 + 400 + 402 = 1510 | 0 |
| 2 | 522 + 1050 + 110 = 1682 | **590** + 56 + 450 + 596 = 1692 | -10 |
| 3 | 746 + **960** + 120 = 1826 | 500 + 64 + 450 + 802 = 1816 | +10 |
| 4 | 997 + 850 + 115 = 1962 | 400 + 72 + 450 + 1040 = 1962 | 0 |

## Notes — coverage
- Fired: nonzero difference, both signs (liability overstated in P2, asset overstated in P3).
- Also tested: the error does not carry into later periods, because the module reads each supplied
  balance directly rather than rolling it. A module that rolled NBV or debt from the prior closing
  would show differences in P3/P4 too, which would be wrong under these rules.
- Ambiguity: none beyond those in three_statements.answer.md.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
