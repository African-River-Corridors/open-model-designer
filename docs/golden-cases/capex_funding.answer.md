# Golden answer: capex_funding

## Outputs
```python
capital_additions = [4200, 3000, 2000, 1100]
debt_funded_capex = [2800, 2100, 1400, 700]
equity_contribution = [1400, 900, 600, 400]
```

## Working (total capex 10,000, debt share 0.7)
| Period | Profile | Capex spend | Dev cost | Capital additions | Debt = 0.7 x spend | Equity = 0.3 x spend + dev | Check: debt + equity = additions |
|---|---|---|---|---|---|---|---|
| 1 | 0.4 | 4000 | 200 | 4200 | 2800 | 1200 + 200 = 1400 | 4200 ok |
| 2 | 0.3 | 3000 | 0 | 3000 | 2100 | 900 + 0 = 900 | 3000 ok |
| 3 | 0.2 | 2000 | 0 | 2000 | 1400 | 600 + 0 = 600 | 2000 ok |
| 4 | 0.1 | 1000 | 100 | 1100 | 700 | 300 + 100 = 400 | 1100 ok |
| Total | 1.0 | 10000 | 300 | 10300 | 7000 | 3300 | 10300 ok |

## Notes
- Rule is clear. Debt share applies to capex only; development cost is all equity. So the overall
  gearing is 7000 / 10300 = 68.0%, not 70%. That is a valid design, but worth a line in the module doc.
- Use a float tolerance (e.g. 1e-9): 0.3 x spend may not be exact in binary floating point.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
