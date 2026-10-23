# Golden request: cash_sweep_percent (OMD M13)
Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the module's code.

Rules, per period (4 periods): sweep = sweep flag x (the amount below); debt after = debt before - sweep; cash after = cash available - sweep.
Amount = min(sweep percent x cash available, debt before sweep).

Inputs: cash_available_for_sweep = [200, 300, 100, 500]; debt_before_sweep = [900, 700, 600, 50];
sweep_flag = [1, 1, 0, 1]; sweep_percent = 0.75
Outputs wanted (4 values each): sweep_amount, debt_after_sweep, cash_after_sweep.
Source kind: hand-calculation (name the reviewer and the date).
