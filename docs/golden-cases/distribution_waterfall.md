# Golden request: distribution_waterfall (OMD M20)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods). The first period's opening hurdle balance is `opening_hurdle_balance`.
- accrual = opening hurdle balance x ((1 + hurdle_rate)^period_years - 1)      (hurdle_rate is per year)
- hurdle balance before paying = opening + accrual + equity contribution       (contributions arrive at period end, earn nothing in the period)
- tier 1 = min(max(distributable cash, 0), hurdle balance before paying)       (paid to the investor)
- closing hurdle balance = before paying - tier 1
- residual cash = max(distributable cash, 0) - tier 1
- sponsor promote = promote_share x residual
- investor distribution = tier 1 + residual - sponsor promote

Inputs:
- distributable_cash = [0, 300, 700, 800]
- equity_contribution = [1000, 0, 200, 0]
- hurdle_rate = 0.21        (so one 0.5-year period accrues exactly 10%: 1.21^0.5 = 1.1)
- period_years = 0.5
- promote_share = 0.2
- opening_hurdle_balance = 0

Outputs wanted (4 values each): hurdle_accrual, hurdle_balance_closing, tier1_distribution, residual_cash,
sponsor_promote, investor_distribution.
Source kind: hand-calculation (name the reviewer and the date).
