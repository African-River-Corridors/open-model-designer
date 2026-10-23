# Golden request: cash_sweep_target_cash (OMD M13)
Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the module's code.

Rules, per period (4 periods): sweep = sweep flag x (the amount below); debt after = debt before - sweep; cash after = cash available - sweep.
Amount = min(max(cash available - target cash, 0), debt before sweep).

Inputs: cash_available_for_sweep = [300, 120, 500, 450]; debt_before_sweep = [800, 700, 650, 100];
sweep_flag = [1, 0, 1, 1]; target_cash = 200
Outputs wanted (4 values each): sweep_amount, debt_after_sweep, cash_after_sweep.
Source kind: hand-calculation (name the reviewer and the date).
