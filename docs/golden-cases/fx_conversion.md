# Golden request: fx_conversion (OMD M15)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods). Rates are units of reporting currency (USD) per unit of local currency (LCU).
The first period's opening rate is `fx_start_rate`; the first period's opening balance is `opening_balance_local`.
- closing rate = opening rate x (1 - depreciation)   (the opening rate is the previous period's closing rate)
- period rate = (opening rate + closing rate) / 2
- flow in USD = flow in LCU x period rate
- closing balance in LCU = opening balance + flow in LCU
- closing balance in USD = closing balance in LCU x closing rate
- translation difference = closing balance in USD - (opening balance in LCU x opening rate) - flow in USD

Inputs:
- fx_start_rate = 0.08
- fx_depreciation = [0.10, 0.05, 0.0, -0.04]     (a negative value is an appreciation)
- flow_local = [1000, -400, 600, 250]
- opening_balance_local = 500

Outputs wanted (4 values each): fx_closing_rate, fx_period_rate, flow_reporting, balance_closing_local,
balance_closing_reporting, fx_translation_difference.
Also helpful: confirm that closing balance in USD = opening balance x start rate + the sum of flows in USD
+ the sum of translation differences, in each period.
Source kind: hand-calculation (name the reviewer and the date).
