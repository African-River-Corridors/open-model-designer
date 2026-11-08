# Golden case returns_irr_4 — answer and working

Calculator: Python `decimal` at 50 digits (a short script of its own,
same method as returns_irr_1). Root cross-check: `numpy.roots`.

## Method

Dates are whole multiples of 365, so years = 0, 1, 2, 3. With x = 1/(1+r), NPV is the cubic
f0 + f1 x + f2 x^2 + f3 x^3. It has at most 3 real roots. The range r in (-0.99, 10] maps to
x in [1/11, 100). A negative x means r < -1, which is out of range.

IRR search: grid of step 0.0001 over (-0.99, 10], bisect each sign change 200 times.
Cross-check: all 3 cubic roots from `numpy.roots`.

## Project

NPV terms at 8%: -1000.000000, 740.740741, 685.871056, -396.916121
- NPV @ 8% = **29.6956764721**
- Cubic roots in x: 1.88609853, 0.89659158, -1.18269011 (last is out of range: r = -1.846)
- IRRs found: **-0.469805004289280**, **0.115335033314822**
- Reported IRR (nearest 0.10): **0.115335033314822**
- NPV @ reported IRR: 4E-47 (zero)
- Signs: - + + -  -> changes at (-1000 -> 800) and (800 -> -500) = **2**
- Unique flag: **0**

## Equity

NPV terms at 12%: -300.000000, 178.571429, 207.270408, -85.413630
- NPV @ 12% = **0.428206997085**
- Cubic roots in x: 2.42910092, 0.89172242, -1.15415667 (last is out of range)
- IRRs found: **-0.588325050303084**, **0.121425213546952**
- Reported IRR (nearest 0.10): **0.121425213546952**
- NPV @ reported IRR: -1.7E-47 (zero)
- Signs: - + + -  -> **2** changes
- Unique flag: **0**

## Cumulative equity cash flow and payback

| Period | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Equity flow | -300 | 200 | 260 | -120 |
| Cumulative | -300 | -100 | 160 | 40 |

Final cumulative 40 >= 0. Periods with cumulative < 0: periods 0 and 1 = 2. Payback = 2 + 1 = **3**.

## Notes for whoever uses this case

- Each series has two IRRs in range. The second one is negative. A solver started at 0.10 must land on the positive one.
- Equity NPV at 12% is small (0.428), because the equity IRR (12.14%) sits just above the 12% rate. A loose tolerance could hide a sign error here.
- Payback is 3 (negative periods + 1). The zero-based index of the first non-negative period is 2, so code that returns that index is off by one.
