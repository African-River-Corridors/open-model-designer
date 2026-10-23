# Golden answer: distribution_waterfall (OMD M20)

## Outputs
```python
hurdle_accrual = [0, 100, 80, 38]
hurdle_balance_closing = [1000, 800, 380, 0]
tier1_distribution = [0, 300, 700, 418]
residual_cash = [0, 0, 0, 382]
sponsor_promote = [0, 0, 0, 76.4]
investor_distribution = [0, 300, 700, 723.6]
```

## Working
Growth factor per period = 1.21^0.5 - 1 = 0.1 (exact in decimal).

| Period | Opening | Accrual = opening x 0.1 | Contribution | Before paying | Dist. cash | Tier 1 = min(max(cash, 0), before) | Closing | Residual | Promote = 0.2 x residual | Investor = tier 1 + residual - promote |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 1000 | 1000 | 0 | min(0, 1000) = 0 | 1000 | 0 | 0 | 0 |
| 2 | 1000 | 100 | 0 | 1100 | 300 | min(300, 1100) = 300 | 800 | 0 | 0 | 300 |
| 3 | 800 | 80 | 200 | 1080 | 700 | min(700, 1080) = 700 | 380 | 0 | 0 | 700 |
| 4 | 380 | 38 | 0 | 418 | 800 | min(800, 418) = 418 | 0 | 382 | 76.4 | 418 + 382 - 76.4 = 723.6 |

Check P4: investor + sponsor = 723.6 + 76.4 = 800 = distributable cash.

Floating-point note: in IEEE doubles, 1.21**0.5 - 1 = 0.10000000000000009, so the accruals compute as
100.00000000000009, 80.00000000000007, 38.000000000000036. This is about 1e-13, well inside a 1e-6
tolerance. The exact values are those in the table.

## Notes — ambiguity
- Same-period contribution can be returned at once. The rule adds the period-end contribution to the
  balance before tier 1 is paid. So in P3 the 200 contributed joins the 1080 that the 700 pays down.
  This matches a period-end convention where contributions and distributions share a date. A model
  that paid distributions before taking in contributions would get the same tier 1 here (700 < 880),
  but the order matters when cash exceeds the pre-contribution balance.
- No GP catch-up. This is a two-tier promote (return of capital plus pref, then an 80/20 split). Many
  promote waterfalls add a catch-up tier between the hurdle and the split. Not in the stated rules, so
  not computed.
- Negative distributable cash is floored to 0 and then dropped. It is not carried forward, and it does
  not add to the hurdle balance. The rules state this; it is not standard if the negative is meant to
  be funded by the investor (then it would be a contribution). Not exercised in this case; see the
  `_2` variant.
- Hurdle accrual compounds on the opening balance only, net of past distributions. This is the usual
  compounding pref convention.

## Notes — coverage
- Fired: zero cash (P1); hurdle not met, tier 1 takes all cash (P2, P3); contribution mid-life (P3);
  hurdle crossed within a period, with residual and promote (P4).
- Not fired: negative distributable cash (the max(·, 0) floor); accrual after the hurdle is cleared
  (opening 0); a contribution after the hurdle is cleared. **Case marked weak.** See
  `distribution_waterfall_2.answer.md`, which fires all three.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
