# Golden answer: vat_account

## Outputs
```python
vat_offset = [50, 150, 100, 80]
vat_net_due = [0, 0, 0, 10]
vat_paid = [0, 0, 0, 6]
vat_payable_closing = [0, 0, 0, 4]
vat_written_off = [0, 0, 0, 0]
vat_receivable_closing = [180, 30, 30, 0]
```

## Working (opening receivable 30, settle share 0.6, write-off at end = 1)
| Period | Recv b/f | Input | Available | Output | Offset = min | Net due | Left over | Written off | Recv c/f | Pay b/f | Paid = b/f + 0.6 x net | Pay c/f |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 30 | 200 | 230 | 50 | 50 | 0 | 180 | 0 (not last) | 180 | 0 | 0 | 0 |
| 2 | 180 | 0 | 180 | 150 | 150 | 0 | 30 | 0 (not last) | 30 | 0 | 0 | 0 |
| 3 | 30 | 100 | 130 | 100 | 100 | 0 | 30 | 0 (not last) | 30 | 0 | 0 | 0 |
| 4 | 30 | 50 | 80 | 90 | 80 | 10 | 0 | 0 (last, but nothing left) | 0 | 0 | 0 + 6 = 6 | 0 + 10 - 6 = 4 |

## Notes
- Rule is clear. Weak coverage, though: the write-off branch fires on 0 (nothing left over in the last
  period), and the payable never carries into a later period, so "paid = b/f + share" is not tested
  with a non-zero b/f. Suggest the builder add a case that makes both bite (e.g. vat_output[3] = 20 gives
  left over 60 written off). Not computed here as it is not the requested case.
- Payable of 4 is left unsettled at the end; no final sweep is in the rules.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
