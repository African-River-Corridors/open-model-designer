# Golden request: cover_ratios (OMD M10)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods):
- DSCR = CFADS / debt service (0 if debt service is 0)
- rolling DSCR = sum of CFADS over the last 2 periods / sum of debt service over the same periods
  (period 1 uses only period 1); 0 if the denominator is 0
- Debt at the start of period t = debt closing of period t-1 (period 1: opening_debt)
- PV of CFADS over the loan life at the start of period t = sum over k >= t of CFADS_k x loan_life_flag_k / (1 + r)^(k - t + 1)
  (each period's cash arrives at the end of its period)
- LLCR_t = that PV / debt at the start of period t; PLCR_t = same with every period's CFADS counted (flag ignored)
- LLCR/PLCR = 0 when debt at the start of the period is 0

Inputs:
- cfads = [400, 380, 360, 340]
- debt_service = [250, 250, 250, 100]
- debt_closing = [800, 600, 300, 0]
- loan_life_flag = [1, 1, 1, 1]
- discount_rate = 0.06
- opening_debt = 1000

Outputs wanted (4 values each): dscr, dscr_rolling, llcr, plcr.
Source kind: hand-calculation (name the reviewer and the date).
