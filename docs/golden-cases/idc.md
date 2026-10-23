# Golden request: idc (OMD M7)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods), opening debt in period 1 = `opening_debt`:
- Interest (IDC) is charged on: opening debt + weight x (this period's draw + this period's IDC), at
  `idc_rate` per period. This is circular (IDC is on both sides); solve it by hand algebraically
  (IDC = rate x (opening + weight x draw) / (1 - weight x rate)).
- Closing debt = opening debt + draw + IDC.
- Capital additions including IDC = capital additions + IDC.

Inputs:
- debt_funded_capex (draw) = [300, 600, 600, 300]
- capital_additions = [450, 900, 900, 450]
- idc_rate = 0.015
- idc_weight = 0.5
- opening_debt = 0

Outputs wanted (4 values each): idc_capitalised, debt_closing, capital_additions_incl_idc.
Source kind: hand-calculation (name the reviewer and the date).
