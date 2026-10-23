# Golden answer: working_capital

## Outputs
```python
receivables = [300.0, 400.0, 500.0, 333.3333333333333]
payables = [270.0, 300.0, 360.0, 250.0]
cash_buffer = [60.0, 66.66666666666667, 80.0, 55.55555555555556]
working_capital = [90.0, 166.66666666666669, 220.0, 138.88888888888886]
working_capital_movement = [40.0, 76.66666666666669, 53.333333333333314, -81.11111111111114]
```
Exact: receivables P4 = 1000/3; cash buffer P2 = 200/3, P4 = 500/9; WC P2 = 500/3, P4 = 1250/9;
movement P2 = 230/3, P3 = 160/3, P4 = -730/9. Compare at ~1e-12.

## Working (days_in_period = 90)
| P | Revenue | Opex | Receivables = Rev x 30/90 | Payables = Opex x 45/90 | Buffer = Opex x 10/90 | WC = Rec + Buf - Pay | Prior WC | Movement |
|---|---|---|---|---|---|---|---|---|
| 1 | 900 | 540 | 300 | 270 | 60 | 300 + 60 - 270 = 90 | 50 (opening) | +40 (uses cash) |
| 2 | 1200 | 600 | 400 | 300 | 66.6667 | 166.6667 | 90 | +76.6667 |
| 3 | 1500 | 720 | 500 | 360 | 80 | 220 | 166.6667 | +53.3333 |
| 4 | 1000 | 500 | 333.3333 | 250 | 55.5556 | 138.8889 | 220 | -81.1111 (release) |
Cross-check: sum of movements = 40 + 76.6667 + 53.3333 - 81.1111 = 88.8889 = 138.8889 - 50. Holds.

## Notes — ambiguity / departure from practice
- **Cash buffer inside working capital.** Standard practice (Bodmer; Yescombe) keeps working capital to
  receivables, inventory and payables. A minimum operating-cash balance is usually a separate reserve or a
  cash-account floor, not a working-capital line. Counting it here moves it through CFADS as a WC movement,
  which lowers CFADS when opex rises. The rule is explicit, so the literal result is the golden.
  Alternative (no buffer): WC = [30, 100, 140, 83.3333]; movements = [-20, 70, 40, -56.6667] (opening 50
  kept as given — note that 50 then implies a prior WC that may itself include a buffer, so the P1
  alternative movement is only indicative).
- Payables are driven by total operating cost. Practice often drives payables from the non-payroll share
  of opex only. Not specified; literal reading used.
- Days are measured against the period's own flow (period-flow x days / days_in_period). That is standard
  for a fixed-length period model; with uneven periods days_in_period should vary by period.

## Notes — coverage (done)
- Fired: positive movement (P1–P3) and a release (P4); opening WC used as the P1 prior value. No floors,
  caps or flags in the rules, so no branch is left unfired.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
