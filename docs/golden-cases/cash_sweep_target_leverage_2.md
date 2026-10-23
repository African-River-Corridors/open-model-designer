# Golden request: cash_sweep_target_leverage, stronger second case (OMD M13)

Why: in the first case the zero floor never bites in a flagged period, period 1 is a tie between the two
caps, and the excess-debt side never binds cleanly below cash. Same rules as `cash_sweep_target_leverage.md`:
amount = min(max(debt before - target leverage x EBITDA, 0), cash available); sweep = flag x amount.

Inputs:
- cash_available_for_sweep = [400, 100, 600, 600]
- debt_before_sweep = [1000, 900, 800, 500]
- ebitda = [300, 300, 320, 340]
- sweep_flag = [1, 1, 1, 1]       # period 4: flagged, debt 500 below 2.5 x 340 = 850 (floor bites)
- target_leverage = 2.5

Expected to be tested: period 1 excess debt 250 < cash 400 (debt cap binds, cash after 150); period 2 cash cap
binds; period 3 excess exactly 0; period 4 floor.

Outputs wanted (4 values each): sweep_amount, debt_after_sweep, cash_after_sweep.
Source kind: hand-calculation (name the reviewer and the date).
