# Golden request: vat_account (OMD M5, open-model-designer PR for #27)

Needed: expected outputs by **hand calculation by a reviewer other than the builder**. Do not use the
module's code. Send numbers and working back to the builder.

Rules, per period (4 periods):
- available = receivable brought forward + input VAT (first period: `opening_vat_receivable`)
- offset = min(available, output VAT); net VAT due = output VAT - offset
- left over = available - offset; written off = left over in the LAST period only if `write_off_at_end`
  is 1, else 0; receivable carried forward = left over - written off
- VAT paid = payable brought forward + settle_share x net VAT due (payable starts at 0)
- payable carried forward = brought forward + net VAT due - paid

Inputs:
- vat_input = [200, 0, 100, 50]
- vat_output = [50, 150, 100, 90]
- opening_vat_receivable = 30
- settle_share = 0.6
- write_off_at_end = 1

Outputs wanted (4 values each): vat_offset, vat_net_due, vat_paid, vat_payable_closing,
vat_written_off, vat_receivable_closing.
Source kind: hand-calculation (name the reviewer and the date).
