# Golden answer: returns (OMD M21)

## Outputs
```python
project_xirr = 0.17253646  # 0.17253646415915672
equity_xirr = 0.27219840  # 0.2721984033427649
project_npv = 177.12711228  # 177.12711227535044
equity_npv = 153.41118427  # 153.41118426782964
# the module repeats each scalar on every period, e.g. project_xirr = [0.17253646415915672] * 4
equity_cumulative_cash = [-500, -500, -200, 450]
equity_payback_period = 4
```

## Working
Years: [0, 365/365, 730/365, 1100/365] = [0, 1, 2, 3.0136986301369864].

Project NPV at 10%:
- 400 / 1.1 = 363.63636364
- 500 / 1.1^2 = 413.22314050
- 800 / 1.1^3.01369863 = 800 / 1.33273891 = 600.26760814
- NPV = -1200 + 363.63636364 + 413.22314050 + 600.26760814 = 177.12711228

Equity NPV at 15%:
- 0 / 1.15 = 0
- 300 / 1.15^2 = 226.84310019
- 650 / 1.15^3.01369863 = 650 / 1.52378958 = 426.56808408
- NPV = -500 + 0 + 226.84310019 + 426.56808408 = 153.41118427

Project XIRR: solved -1200 + 400/(1+r) + 500/(1+r)^2 + 800/(1+r)^3.01369863 = 0 (scipy brentq, one
expression, xtol 1e-15). r = 0.17253646415915672. Check terms at r: 341.14077662 + 363.67821711 +
495.18100627 = 1200.00000000; residual 1.1e-13.

Equity XIRR: solved -500 + 300/(1+r)^2 + 650/(1+r)^3.01369863 = 0. r = 0.2721984033427649. Check:
185.35809712 + 314.64190288 = 500.00000000; residual -5.7e-14.

Both XIRRs are unique: each series has one sign change (Descartes), so there is one real root.

Cumulative equity: -500; -500 + 0 = -500; -500 + 300 = -200; -200 + 650 = 450.
Payback: first period with cumulative >= 0 is period 4.

## Notes — ambiguity
- NPV discounts to the first flow's date, and the first flow is undiscounted. This is Excel's XNPV, not
  Excel's NPV (which discounts the first flow by one period). Under Excel NPV with periodic exponents
  1-4 the project NPV would differ. The rule is clear, so the XNPV form is used.
- Payback is a whole period number, not interpolated. Bodmer and most lender models interpolate within
  the period (here: 200/650 = 0.31 of the way from flow 3 to flow 4, so about
  2 + 0.31 x 1.0137 = 2.31 years after the first flow). The rule asks for the integer period, so 4.
- Non-annual last gap (365, 365, 370 days) is handled by the actual/365 year fraction, as in Excel XIRR.

## Notes — coverage
- Fired: payback found, strict (cumulative > 0 in P4); a zero flow (equity P2); a non-integer year
  fraction (P4).
- Not fired: payback where cumulative is exactly 0 (the >= edge); no payback (return 0); a negative
  XIRR. **Case marked weak.** Payback is one number per case, so two variants are given:
  `returns_2.answer.md` (cumulative hits exactly 0) and `returns_3.answer.md` (never pays back,
  negative XIRR).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
