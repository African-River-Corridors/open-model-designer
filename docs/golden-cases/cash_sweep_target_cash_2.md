# Golden request: cash_sweep_target_cash, stronger second case (OMD M13)

Why: in the first case the zero floor and the flag-0 branch fire in the same period, so a module without
the floor passes. Same rules as `cash_sweep_target_cash.md`: amount = min(max(cash - target cash, 0), debt before sweep);
sweep = flag x amount; debt after = debt before - sweep; cash after = cash - sweep.

Inputs:
- cash_available_for_sweep = [300, 120, 500, 450]
- debt_before_sweep = [800, 700, 650, 100]
- sweep_flag = [1, 1, 1, 0]       # period 2: flagged, cash below the 200 target; period 4: flag off with excess cash
- target_cash = 200

Outputs wanted (4 values each): sweep_amount, debt_after_sweep, cash_after_sweep.
Source kind: hand-calculation (name the reviewer and the date).
