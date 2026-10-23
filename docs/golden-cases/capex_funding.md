# Golden request: capex_funding (OMD M6)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back to the builder.

Rules, per period (4 periods):
- capex spend = total capex x spend profile (share of the total in the period)
- capital additions = capex spend + development cost
- debt-funded capex = debt share x capex spend
- equity contribution = (1 - debt share) x capex spend + development cost (development cost is all equity)

Inputs:
- total_capex = 10000
- spend_profile = [0.4, 0.3, 0.2, 0.1]
- development_cost = [200, 0, 0, 100]
- debt_share = 0.7

Outputs wanted (4 values each): capital_additions, debt_funded_capex, equity_contribution.
Source kind: hand-calculation (name the reviewer and the date).
