# Golden answer: tax_engine

## Outputs
```python
taxable_profit = [1100, 0, 350, 800]
tax_charge = [330, 10, 105, 240]
tax_paid = [247.5, 90, 81.25, 206.25]
tax_payable_closing = [82.5, 2.5, 26.25, 60]
```

## Working (rate 0.3, instalment share 0.75, opening payable 0)
| Period | PBT + adj - losses | Taxable = max(.,0) | 0.3 x taxable | Charge = max(., min tax 10) | B/f | Paid = b/f + 0.75 x charge | C/f = b/f + charge - paid |
|---|---|---|---|---|---|---|---|
| 1 | 1000 + 100 - 0 = 1100 | 1100 | 330 | 330 | 0 | 0 + 247.5 = 247.5 | 0 + 330 - 247.5 = 82.5 |
| 2 | -300 + 0 - 0 = -300 | 0 | 0 | 10 | 82.5 | 82.5 + 7.5 = 90 | 82.5 + 10 - 90 = 2.5 |
| 3 | 600 - 50 - 200 = 350 | 350 | 105 | 105 | 2.5 | 2.5 + 78.75 = 81.25 | 2.5 + 105 - 81.25 = 26.25 |
| 4 | 900 + 0 - 100 = 800 | 800 | 240 | 240 | 26.25 | 26.25 + 180 = 206.25 | 26.25 + 240 - 206.25 = 60 |

## Notes
- Rule is clear. Minimum tax is charged in the loss period (period 2: 10 on zero profit), as the rule says.
- `losses_relieved` is an input, not derived from the period 2 loss; the case does not check that the
  relief (300 total) matches losses available. Fine for a unit golden.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
