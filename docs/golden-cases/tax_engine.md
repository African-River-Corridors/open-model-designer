# Golden request: tax_engine (OMD M4, open-model-designer PR for #26)

Needed: expected outputs by **hand calculation by a reviewer other than the builder**. Do not use the
module's code. Send numbers and working back to the builder.

Rules, per period (4 periods):
- taxable profit = max(profit before tax + adjustments - losses relieved, 0)
- charge = max(tax rate x taxable profit, minimum tax)
- tax paid = liability brought forward + instalment share x charge
- liability carried forward = brought forward + charge - paid (the first period's brought-forward is
  `opening_tax_payable`)

Inputs:
- profit_before_tax = [1000, -300, 600, 900]
- tax_adjustments = [100, 0, -50, 0]
- losses_relieved = [0, 0, 200, 100]
- minimum_tax = [10, 10, 10, 10]
- tax_rate = 0.3
- instalment_share = 0.75
- opening_tax_payable = 0

Outputs wanted (4 values each): taxable_profit, tax_charge, tax_paid, tax_payable_closing.
Source kind: hand-calculation (name the reviewer and the date).
