# Golden answer: tax_pool_sl

## Outputs
```python
tax_allowance = [0, 287.5, 575, 775]
tax_wdv_close = [2000, 2012.5, 1437.5, 1462.5]
```

## Working (rate 0.25, opening WDV 0)
| Period | Opening WDV | Additions | Pool before | Cumulative cost | Use | Uncapped = use x 0.25 x cum cost | Cap (pool) | Allowance | Closing WDV |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 2000 | 2000 | 2000 | 0 | 0 | 2000 | 0 | 2000 |
| 2 | 2000 | 300 | 2300 | 2300 | 0.5 | 0.5 x 0.25 x 2300 = 287.5 | 2300 | 287.5 | 2012.5 |
| 3 | 2012.5 | 0 | 2012.5 | 2300 | 1 | 1 x 0.25 x 2300 = 575 | 2012.5 | 575 | 1437.5 |
| 4 | 1437.5 | 800 | 2237.5 | 3100 | 1 | 1 x 0.25 x 3100 = 775 | 2237.5 | 775 | 1462.5 |

The cap does not bind in any period.

## Notes
- Rule is clear for these inputs.
- Cumulative cost counts opening WDV as if it were cost. Textbook straight line runs on original
  cost, not WDV. Opening WDV is 0 here, so the result is the same either way; the case does not test it.
- Pooled straight line (one cost base) differs from per-asset straight line once an early vintage is
  fully relieved. That point is not reached in 4 periods, so no alternative number arises.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
