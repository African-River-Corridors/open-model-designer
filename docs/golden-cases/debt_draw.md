# Golden request: debt_draw (OMD M8)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods), debt drawn at the start of period 1 = `opening_debt`:
- headroom = facility limit - debt drawn so far
- drawdown = min(funding need x availability flag, headroom)
- funding gap = funding need - drawdown (need not met; shown, never plugged)
- closing debt drawn = opening + drawdown

Inputs:
- funding_need = [250, 350, 300, 150]
- availability_flag = [1, 1, 1, 0]
- facility_limit = 800
- opening_debt = 50

Outputs wanted (4 values each): debt_drawdown, funding_gap, debt_closing.
Source kind: hand-calculation (name the reviewer and the date).
