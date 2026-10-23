# Golden request: returns (OMD M21)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back. Give each XIRR to at least 8 decimal places (the test compares to 1e-6).

Rules. Four dated flows for each of two holders. years = (date - first date) / 365 (dates are whole days).
- NPV = sum over flows of flow / (1 + discount rate)^years   (discounted to the first flow's date)
- XIRR = the annual rate r with sum of flow / (1 + r)^years = 0   (365-day year; same as Excel's XIRR)
- equity cumulative cash flow = running sum of equity cash flow
- equity payback period = the number (1 to 4) of the first period whose cumulative equity cash is >= 0; 0 if none

Inputs:
- project_cash_flow = [-1200, 400, 500, 800]
- equity_cash_flow = [-500, 0, 300, 650]
- flow_dates = [0, 365, 730, 1100]       (so years = 0, 1, 2, 3.0137...)
- project_discount_rate = 0.10
- equity_discount_rate = 0.15
- days_per_year = 365

Outputs wanted: project_xirr, equity_xirr, project_npv, equity_npv (one number each; the module repeats it on every period),
equity_cumulative_cash (4 values), equity_payback_period (one number).
Source kind: hand-calculation (name the reviewer and the date).
