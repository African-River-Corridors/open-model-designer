# Golden request: tax_pool_rb (OMD M2, open-model-designer PR for #24)

Needed: expected outputs by **hand calculation by a reviewer other than the builder**, from the
rules below. Do not use the module's code. Send the numbers (and the working) back to the builder.

Rules (reducing balance), one pool, 4 periods:
- pool before allowance = opening WDV + additions in the period
- allowance = use_fraction x rate x pool before allowance
- closing WDV = pool before allowance - allowance

Inputs:
- capital_additions = [2000, 300, 0, 800]
- use_fraction = [0, 0.5, 1, 1]
- allowance_rate = 0.25
- opening_wdv = 0

Outputs wanted (4 values each): tax_allowance, tax_wdv_close.
Source kind: hand-calculation (name the reviewer and the date).
