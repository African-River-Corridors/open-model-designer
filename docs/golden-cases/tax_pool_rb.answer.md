# Golden answer: tax_pool_rb

## Outputs
```python
tax_allowance = [0, 287.5, 503.125, 577.34375]
tax_wdv_close = [2000, 2012.5, 1509.375, 1732.03125]
```

## Working (rate 0.25, opening WDV 0)
| Period | Opening WDV | Additions | Pool before | Use | Allowance = use x 0.25 x pool | Closing WDV |
|---|---|---|---|---|---|---|
| 1 | 0 | 2000 | 2000 | 0 | 0 x 0.25 x 2000 = 0 | 2000 |
| 2 | 2000 | 300 | 2300 | 0.5 | 0.5 x 0.25 x 2300 = 287.5 | 2012.5 |
| 3 | 2012.5 | 0 | 2012.5 | 1 | 1 x 0.25 x 2012.5 = 503.125 | 1509.375 |
| 4 | 1509.375 | 800 | 2309.375 | 1 | 1 x 0.25 x 2309.375 = 577.34375 | 1732.03125 |

## Notes
- Rule is clear. The literal reading keeps the unclaimed share (1 - use) in the pool for later.
- Departure from one textbook convention: under a private-use rule (e.g. UK), the pool falls by the
  full rate x pool, and only the business share is claimed; the private share is lost. That is only
  relevant if `use_fraction` means private use, not "not yet in use". Alternative under that reading:
  tax_allowance = [0, 225, 337.5, 453.125]; tax_wdv_close = [1500, 1350, 1012.5, 1359.375].
  I read `use_fraction` as an in-service share, so the literal result above is the golden.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
