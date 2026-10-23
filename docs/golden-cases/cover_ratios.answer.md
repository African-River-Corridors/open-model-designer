# Golden answer: cover_ratios

## Outputs
```python
dscr = [1.6, 1.52, 1.44, 3.4]
dscr_rolling = [1.6, 1.56, 1.48, 2.0]
llcr = [1.2871319251640045, 1.2054498008423058, 1.0703690518571258, 1.069182389937107]
plcr = [1.2871319251640045, 1.2054498008423058, 1.0703690518571258, 1.069182389937107]
```
Rounded: LLCR = PLCR = [1.2871, 1.2054, 1.0704, 1.0692].

## Working — DSCR
| Period | CFADS | Debt service | DSCR | Rolling CFADS (last 2) | Rolling DS (last 2) | Rolling DSCR |
|---|---|---|---|---|---|---|
| 1 | 400 | 250 | 1.60 | 400 | 250 | 1.60 |
| 2 | 380 | 250 | 1.52 | 780 | 500 | 1.56 |
| 3 | 360 | 250 | 1.44 | 740 | 500 | 1.48 |
| 4 | 340 | 100 | 3.40 | 700 | 350 | 2.00 |

## Working — LLCR / PLCR (r = 0.06, end-of-period cash)
Discounted CFADS terms seen from the start of period 1: 400/1.06 = 377.3585, 380/1.06^2 = 338.1986,
360/1.06^3 = 302.2629, 340/1.06^4 = 269.3118.
| Period t | Debt at start | PV of CFADS k >= t | Working | LLCR = PV / debt |
|---|---|---|---|---|
| 1 | 1000 (opening) | 1287.1319 | 377.3585 + 338.1986 + 302.2629 + 269.3118 | 1.287132 |
| 2 | 800 | 964.3598 | 380/1.06 + 360/1.06^2 + 340/1.06^3 | 1.205450 |
| 3 | 600 | 642.2214 | 360/1.06 + 340/1.06^2 | 1.070369 |
| 4 | 300 | 320.7547 | 340/1.06 | 1.069182 |
Cross-check: PV_t = (PV_t-1 x 1.06) - CFADS_t-1. E.g. 1287.1319 x 1.06 - 400 = 964.3598. Holds.
PLCR: every loan-life flag is 1 and there is no CFADS after period 4, so PLCR = LLCR in every period.

## Notes
- Rules are clear; results follow the literal reading. Three coverage gaps:
  1. LLCR and PLCR give identical values, so this case cannot tell them apart. Add a case with a flag of 0
     in period 4 (then LLCR_1 = (377.3585 + 338.1986 + 302.2629) / 1000 = 1.017820, PLCR unchanged).
  2. No zero-denominator branch fires (debt service and debt at start are never 0).
  3. Inputs are not internally consistent: debt at start of period 4 is 300 and closing is 0, but debt
     service is only 100. The ratios do not depend on this, but a reader may flag it.
- Rolling DSCR here is backward-looking (last 2 periods). Many lenders test a forward-looking or
  historic 12-month window; the rule as written is fine but name the convention in the module doc.
- Standard practice discounts LLCR at the debt interest rate; here discount_rate is a free input.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
