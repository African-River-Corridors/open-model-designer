# Golden answer: vat_account, second case

## Outputs — Case A
```python
vat_offset = [50, 150, 100, 20]
vat_net_due = [0, 0, 0, 0]
vat_paid = [0, 0, 0, 0]
vat_payable_closing = [0, 0, 0, 0]
vat_written_off = [0, 0, 0, 60]
vat_receivable_closing = [180, 30, 30, 0]
```

## Outputs — Case B
```python
vat_offset = [0, 0, 0, 0]
vat_net_due = [100, 40, 0, 0]
vat_paid = [60, 64, 16, 0]
vat_payable_closing = [40, 16, 0, 0]
vat_written_off = [0, 0, 0, 0]
vat_receivable_closing = [0, 0, 0, 0]
```

## Working — Case A (opening receivable 30, settle share 0.6, write-off at end = 1)
| Period | Recv b/f | Input | Available | Output | Offset = min | Net due | Left over | Written off | Recv c/f | Pay b/f | Paid = b/f + 0.6 x net | Pay c/f |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 30 | 200 | 230 | 50 | 50 | 0 | 180 | 0 (not last) | 180 | 0 | 0 | 0 |
| 2 | 180 | 0 | 180 | 150 | 150 | 0 | 30 | 0 (not last) | 30 | 0 | 0 | 0 |
| 3 | 30 | 100 | 130 | 100 | 100 | 0 | 30 | 0 (not last) | 30 | 0 | 0 | 0 |
| 4 | 30 | 50 | 80 | 20 | 20 | 0 | 60 | 60 (last) | 0 | 0 | 0 | 0 |

## Working — Case B (opening receivable 0, settle share 0.6, write-off at end = 1)
| Period | Recv b/f | Input | Available | Output | Offset | Net due | Left over | Written off | Recv c/f | Pay b/f | Paid = b/f + 0.6 x net | Pay c/f = b/f + net - paid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 0 | 100 | 0 | 100 | 0 | 0 | 0 | 0 | 0 + 60 = 60 | 0 + 100 - 60 = 40 |
| 2 | 0 | 0 | 0 | 40 | 0 | 40 | 0 | 0 | 0 | 40 | 40 + 24 = 64 | 40 + 40 - 64 = 16 |
| 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 16 + 0 = 16 | 16 + 0 - 16 = 0 |
| 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
Check: total paid 140 = total net due 140; nothing left payable at the end.

## Notes
- Rules are clear. Case A fires the write-off (60) and Case B carries a non-zero payable b/f in
  periods 2 and 3, as intended.
- Case A still never carries a payable (net due is 0 throughout); Case B covers that, so together they are complete.
- Practice note, not an error: writing off an unused input-VAT balance at the end assumes no refund
  claim. Where a refund can be claimed, model it as an explicit assumption.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
