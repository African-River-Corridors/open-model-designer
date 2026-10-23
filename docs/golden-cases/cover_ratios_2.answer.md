# Golden answer: cover_ratios_2

## Outputs
```python
dscr = [1.6, 1.52, 0.5580391743500394, 0]
dscr_rolling = [1.6, 1.56, 0.8267084936477507, 1.0850761723472988]
llcr = [1.0178200796630776, 0.8381349190652619, 0.5580391743500394, 0]
plcr = [1.2871319251640045, 1.1905677045356107, 1.0552438894417933, 0]
```
Rounded: DSCR [1.6000, 1.5200, 0.5580, 0]; rolling [1.6000, 1.5600, 0.8267, 1.0851];
LLCR [1.0178, 0.8381, 0.5580, 0]; PLCR [1.2871, 1.1906, 1.0552, 0].
(Last-digit float differences are possible depending on summation order; compare at ~1e-12 relative.)

## Working — DSCR
| Period | CFADS | Debt service | DSCR | Rolling CFADS (last 2) | Rolling DS (last 2) | Rolling DSCR |
|---|---|---|---|---|---|---|
| 1 | 400 | 250 | 1.6000 | 400 | 250 | 1.6000 |
| 2 | 380 | 250 | 1.5200 | 780 | 500 | 1.5600 |
| 3 | 360 | 645.116 | 0.5580 | 740 | 895.116 | 0.8267 |
| 4 | 340 | 0 | 0 (DS = 0) | 700 | 645.116 | 1.0851 |

## Working — LLCR / PLCR (r = 0.06, end-of-period cash)
Discounted CFADS seen from the start of P1: 377.3585, 338.1986, 302.2629, 269.3118 (P4, flag 0).
| Period t | Debt at start | PV flagged CFADS k >= t (LLCR) | PV all CFADS k >= t (PLCR) | LLCR | PLCR |
|---|---|---|---|---|---|
| 1 | 1000 (opening) | 377.3585 + 338.1986 + 302.2629 = 1017.8201 | + 269.3118 = 1287.1319 | 1.017820 | 1.287132 |
| 2 | 810 | 380/1.06 + 360/1.06^2 = 678.8893 | + 340/1.06^3 = 964.3598 | 0.838135 | 1.190568 |
| 3 | 608.6 | 360/1.06 = 339.6226 | + 340/1.06^2 = 642.2214 | 0.558039 | 1.055244 |
| 4 | 0 | — | — | 0 (debt 0) | 0 (debt 0) |
Cross-check: P3 LLCR = (360/1.06)/608.6 = 360/(608.6 x 1.06) = 360/645.116 = P3 DSCR. A single
remaining period with a bullet clear-out must give LLCR = DSCR. Holds.
Cross-check: PLCR PV_t = PV_t-1 x 1.06 - CFADS_t-1: 1287.1319 x 1.06 - 400 = 964.3598. Holds.

## Notes — ambiguity
- Rolling DSCR in P4 uses a window where only P3 had debt service, giving 700/645.116 = 1.085 after the
  loan is repaid. That is the literal rule. Common practice reports no DSCR (or n/a) once debt is repaid;
  under that alternative, rolling P4 = 0. Worth naming in the module doc.
- Standard practice discounts LLCR at the debt rate; here 6% matches the implied loan rate, which is good.

## Notes — coverage (done, one minor gap)
- Fired: LLCR differs from PLCR (P1–P3, flag 0 in P4); DSCR zero-denominator (P4); LLCR/PLCR zero-debt
  branch (P4); rolling window of one period (P1) and two (P2–P4). Inputs are internally consistent.
- Not fired: rolling-DSCR zero-denominator (needs two consecutive periods with debt service 0).
  Minor: add a fifth period with DS 0 (expect rolling 0).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
