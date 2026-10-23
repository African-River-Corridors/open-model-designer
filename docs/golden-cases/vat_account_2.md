# Golden request: vat_account, second case (OMD M5, open-model-designer PR #51)

Why: the first golden case never fires the write-off (nothing is left over in the last period) and
never carries a VAT payable into a later period, so `paid = payable b/f + share x net due` is not
tested with a non-zero b/f. This case makes both bite. Needed: expected outputs by hand calculation by
a reviewer other than the builder. Same rules as `vat_account.md`.

Inputs:
- vat_input = [200, 0, 100, 50]
- vat_output = [50, 150, 100, 20]    # last period: output 20 leaves 60 of receivable to write off
- opening_vat_receivable = 30
- settle_share = 0.6
- write_off_at_end = 1

A second input set so the payable carries (net due in an early period):
- Case B: vat_input = [0, 0, 0, 0], vat_output = [100, 40, 0, 0], opening_vat_receivable = 0,
  settle_share = 0.6, write_off_at_end = 1  (payable b/f is non-zero in periods 2 and 3)

Outputs wanted for each case (4 values each): vat_offset, vat_net_due, vat_paid, vat_payable_closing,
vat_written_off, vat_receivable_closing.
Source kind: hand-calculation (name the reviewer and the date).
