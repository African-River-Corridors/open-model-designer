# Golden request: cash_sweep_target_leverage (OMD M13)
Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the module's code.

Rules, per period (4 periods): sweep = sweep flag x (the amount below); debt after = debt before - sweep; cash after = cash available - sweep.
Amount = min(max(debt before sweep - target leverage x EBITDA, 0), cash available).

Inputs: cash_available_for_sweep = [250, 100, 600, 600]; debt_before_sweep = [1000, 900, 800, 500];
ebitda = [300, 300, 320, 340]; sweep_flag = [1, 1, 1, 0]; target_leverage = 2.5
Outputs wanted (4 values each): sweep_amount, debt_after_sweep, cash_after_sweep.
Source kind: hand-calculation (name the reviewer and the date).
