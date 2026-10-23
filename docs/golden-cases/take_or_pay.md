# Golden request: take_or_pay (OMD M18)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods):
- sales = delivered volume x unit price
- shortfall volume = max(contracted minimum - delivered volume, 0)
- shortfall payment = shortfall volume x unit price x shortfall_payment_share
- revenue = sales + shortfall payment

Inputs:
- contracted_minimum = [100, 100, 100, 100]
- delivered_volume = [120, 80, 100, 0]     (above the minimum; below; exactly at it; nothing delivered)
- unit_price = 50
- shortfall_payment_share = 0.8

Outputs wanted (4 values each): sales_revenue, shortfall_volume, shortfall_payment, revenue.
Source kind: hand-calculation (name the reviewer and the date).
