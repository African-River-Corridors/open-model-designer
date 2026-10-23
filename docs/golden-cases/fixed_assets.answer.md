# Golden answer: fixed_assets

## Outputs
```python
depreciation = [0, 230, 460, 620]
fa_gross_closing = [2000, 2300, 2300, 3100]
fa_accum_depreciation_closing = [0, 230, 690, 1310]
fa_nbv_closing = [2000, 2070, 1610, 1790]
```

## Working (useful life 5, opening gross 0, opening accumulated depreciation 0)
| Period | Gross b/f | Additions | Gross c/f | Accum b/f | NBV before | Gross / 5 | min | Use | Depreciation | Accum c/f | NBV |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 2000 | 2000 | 0 | 2000 | 400 | 400 | 0 | 0 | 0 | 2000 |
| 2 | 2000 | 300 | 2300 | 0 | 2300 | 460 | 460 | 0.5 | 230 | 230 | 2070 |
| 3 | 2300 | 0 | 2300 | 230 | 2070 | 460 | 460 | 1 | 460 | 690 | 1610 |
| 4 | 2300 | 800 | 3100 | 690 | 2410 | 620 | 620 | 1 | 620 | 1310 | 1790 |

The NBV cap does not bind in any period.

## Notes
- Rule is clear for these inputs.
- Departure from IAS 16 practice: depreciation is pooled on total gross cost, not per asset from its
  available-for-use date, and a partial "share in use" stretches the effective life. The two methods only
  diverge once an early vintage is fully depreciated, which does not happen in 4 periods. No alternative
  number arises.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
