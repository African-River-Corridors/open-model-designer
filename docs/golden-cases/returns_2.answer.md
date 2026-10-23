# Golden answer: returns_2 (variant of OMD M21 — payback on exactly zero)

## Inputs (same rules as returns; only equity_cash_flow changed)
- project_cash_flow = [-1200, 400, 500, 800]
- equity_cash_flow = [-500, 200, 300, 100]
- flow_dates = [0, 365, 730, 1100]       (years = 0, 1, 2, 3.0136986301369864)
- project_discount_rate = 0.10
- equity_discount_rate = 0.15
- days_per_year = 365
- Rules: NPV = sum flow / (1 + rate)^years; XIRR as Excel (365-day); cumulative = running sum of
  equity; payback = first period (1-4) with cumulative >= 0, else 0.

## Outputs
```python
project_xirr = 0.17253646  # 0.17253646415915672 (unchanged from returns)
equity_xirr = 0.10587176  # 0.10587176417269295
project_npv = 177.12711228  # 177.12711227535044 (unchanged)
equity_npv = -33.61799724  # -33.61799724365798
equity_cumulative_cash = [-500, -300, 0, 100]
equity_payback_period = 3
```

## Working
Equity NPV at 15%: 200/1.15 = 173.91304348; 300/1.15^2 = 226.84310019; 100/1.15^3.01369863 =
65.62585909. NPV = -500 + 466.38200276 = -33.61799724.

Equity XIRR: solved -500 + 200/(1+r) + 300/(1+r)^2 + 100/(1+r)^3.01369863 = 0 (brentq, one expression).
r = 0.10587176417269295; residual -2.0e-13. One sign change, so one root.

Cumulative: -500; -300; 0; 100. Period 3 is exactly 0, which meets ">= 0", so payback = 3.
A module that used "> 0" would return 4. This case tests that edge.

Project outputs: see returns.answer.md.

## Notes — coverage
- Fired: payback on cumulative exactly 0 (the >= edge); negative NPV with positive XIRR (XIRR below the
  15% rate).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
