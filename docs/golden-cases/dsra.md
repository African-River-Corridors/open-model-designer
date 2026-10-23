# Golden request: dsra (OMD M11) - rules as ruled by the coordinator

Rules, per period (4 periods), balance brought forward in period 1 = opening_dsra:
- target = SUM of the NEXT TWO periods' debt service (periods after the current one; fewer at the end; last period 0)
- top-up = min(max(target - balance b/f, 0), cash available) x funding gate
- release = max(balance b/f - target, 0)
- closing = b/f + top-up - release
Inputs: debt_service = [0, 300, 300, 100]; cash_available_for_dsra = [400, 100, 400, 400]; dsra_funding_gate = [1, 1, 0, 1]; opening_dsra = 50
(there is no dsra_target_periods input any more)
Outputs wanted: dsra_target, dsra_transfer_in, dsra_release, dsra_closing. Answered: see dsra.answer.md (standard-practice reading).
