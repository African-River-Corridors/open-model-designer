# Golden request: cfads (OMD M17)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods):
- CFADS before tax = revenue - operating cost - working capital movement
  (a positive movement uses cash; a negative movement, a release, adds to CFADS)
- CFADS = CFADS before tax - tax paid

Inputs:
- revenue = [800, 1000, 1200, 900]
- operating_cost = [350, 400, 450, 380]
- working_capital_movement = [120, 60, -30, -80]
- tax_paid = [0, 40, 100, 70]

Outputs wanted (4 values each): cfads_pre_tax, cfads.
Source kind: hand-calculation (name the reviewer and the date).
