# Golden request: cash_waterfall (OMD M19)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Four tiers, in this order: operating_costs, senior_service, reserve_top_up, sub_service. 4 periods.
Per period:
- each tier is paid min(its claim, max(cash left before the tier, 0)); the first tier starts from cash_available
- cash left after a tier = cash left before it - what it was paid
- unpaid = claim - paid
- cash_remainder = cash left after the last tier (negative when cash_available is negative)

Inputs:
- cash_available = [1500, 900, 250, -50]
- claim_operating_costs = [200, 200, 200, 200]
- claim_senior_service = [500, 500, 500, 500]
- claim_reserve_top_up = [100, 100, 100, 100]
- claim_sub_service = [300, 300, 300, 300]

Outputs wanted (4 values each): paid_operating_costs, paid_senior_service, paid_reserve_top_up, paid_sub_service,
unpaid_operating_costs, unpaid_senior_service, unpaid_reserve_top_up, unpaid_sub_service, cash_remainder.
Source kind: hand-calculation (name the reviewer and the date).
