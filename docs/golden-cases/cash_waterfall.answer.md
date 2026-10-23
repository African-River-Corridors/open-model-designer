# Golden answer: cash_waterfall (OMD M19)

## Outputs
```python
paid_operating_costs = [200, 200, 200, 0]
paid_senior_service = [500, 500, 50, 0]
paid_reserve_top_up = [100, 100, 0, 0]
paid_sub_service = [300, 100, 0, 0]
unpaid_operating_costs = [0, 0, 0, 200]
unpaid_senior_service = [0, 0, 450, 500]
unpaid_reserve_top_up = [0, 0, 100, 100]
unpaid_sub_service = [0, 200, 300, 300]
cash_remainder = [400, 0, 0, -50]
```

## Working
Each tier: paid = min(claim, max(cash before, 0)); cash after = cash before - paid.

| Period | Cash avail | Opex 200: paid / left | Senior 500: paid / left | Reserve 100: paid / left | Sub 300: paid / left | Remainder |
|---|---|---|---|---|---|---|
| 1 | 1500 | min(200, 1500) = 200 / 1300 | min(500, 1300) = 500 / 800 | min(100, 800) = 100 / 700 | min(300, 700) = 300 / 400 | 400 |
| 2 | 900 | 200 / 700 | 500 / 200 | 100 / 100 | min(300, 100) = 100 / 0 | 0 |
| 3 | 250 | 200 / 50 | min(500, 50) = 50 / 0 | min(100, 0) = 0 / 0 | 0 / 0 | 0 |
| 4 | -50 | min(200, max(-50, 0)) = 0 / -50 | 0 / -50 | 0 / -50 | 0 / -50 | -50 |

Unpaid = claim - paid: P2 sub 300 - 100 = 200; P3 senior 500 - 50 = 450, reserve 100, sub 300; P4 every tier
unpaid in full (200, 500, 100, 300).

Check: sum of paid + remainder = cash available in P1-P3 (1100 + 400 = 1500; 900 + 0 = 900; 250 + 0 = 250).
In P4, paid 0 and remainder -50 = cash available.

## Notes — ambiguity
- No ambiguity in the stated rules. Two points depart from usual project-finance practice (Yescombe,
  Bodmer). The literal rules are computed above.
  - Unpaid claims do not carry forward. In a usual model, unpaid senior debt service becomes arrears
    (and an event of default), and the reserve shortfall stays as next period's top-up claim. Here,
    each period stands alone. If the module carried arrears, P4 claims would be larger. Its paid
    figures would still be 0, because P4 cash is negative.
  - Negative cash passes to cash_remainder unchanged. A usual model funds a negative CFADS from the
    DSRA, a standby facility or equity. Here, the -50 is only reported.
- Tier order (reserve top-up above sub-debt service) matches usual practice.

## Notes — coverage
- min picks the claim (tier paid in full): P1 all tiers; P2 opex, senior, reserve.
- min picks the cash (tier runs short, partial pay): P2 sub (100 of 300); P3 senior (50 of 500).
- tier gets 0 because cash is exactly 0: P3 reserve and sub.
- max floors negative cash to 0: P4, every tier, from the first tier on.
- zero remainder after a partial tier: P2 and P3. Positive remainder: P1. Negative remainder: P4.
- Not fired: the first tier running short with positive cash (0 < cash < 200). It uses the same rule as
  the other tiers, and that rule's partial branch fires in P2 and P3, so I do not mark the case weak.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
