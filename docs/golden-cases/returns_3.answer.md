# Golden answer: returns_3 (variant of OMD M21 — no payback, negative XIRR)

## Inputs (same rules as returns; only equity_cash_flow changed)
- project_cash_flow = [-1200, 400, 500, 800]
- equity_cash_flow = [-500, 100, 100, 100]
- flow_dates = [0, 365, 730, 1100]       (years = 0, 1, 2, 3.0136986301369864)
- project_discount_rate = 0.10
- equity_discount_rate = 0.15
- days_per_year = 365
- Rules: as in returns.

## Outputs
```python
project_xirr = 0.17253646  # 0.17253646415915672 (unchanged from returns)
equity_xirr = -0.21712003  # -0.21712003427321935
project_npv = 177.12711228  # 177.12711227535044 (unchanged)
equity_npv = -271.80325244  # -271.8032524421458
equity_cumulative_cash = [-500, -400, -300, -200]
equity_payback_period = 0
```

## Working
Equity NPV at 15%: 100/1.15 = 86.95652174; 100/1.15^2 = 75.61436673; 100/1.15^3.01369863 =
65.62585909. NPV = -500 + 228.19674756 = -271.80325244.

Equity XIRR: solved -500 + 100/(1+r) + 100/(1+r)^2 + 100/(1+r)^3.01369863 = 0 (brentq on [-0.9, 1],
one expression). r = -0.21712003427321935; residual 0.0. One sign change, so one root. Excel XIRR
returns the same negative rate (it may need a negative guess to converge).

Cumulative: -500; -400; -300; -200. Never >= 0, so payback = 0.

## Notes — coverage
- Fired: no payback (returns 0); negative XIRR.
- Ambiguity: none beyond those in returns.answer.md. A module that returned None, NaN or 5 for "no
  payback" would fail; the rule says 0.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
