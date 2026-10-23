# Golden answer: dsra

## Outputs (literal reading)
```python
dsra_target = [600, 600, 200, 0]
dsra_transfer_in = [400, 100, 0, 0]
dsra_release = [0, 0, 350, 200]
dsra_closing = [450, 550, 200, 0]
```

## Working (target periods 2; target = 2 x next period's debt service)
| Period | B/f | Next DS | Target | Shortfall = max(target - b/f, 0) | Cash avail | Gate | Top-up | Release = max(b/f - target, 0) | Closing |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 50 | 300 | 600 | 550 | 400 | 1 | min(550, 400) x 1 = 400 | 0 | 450 |
| 2 | 450 | 300 | 600 | 150 | 100 | 1 | min(150, 100) x 1 = 100 | 0 | 550 |
| 3 | 550 | 100 | 200 | 0 | 400 | 0 | 0 | 350 | 200 |
| 4 | 200 | none | 0 | 0 | 400 | 1 | 0 | 200 | 0 |

## Notes — ambiguity
- The rule sizes the target as 2 x ONE next period's debt service. Standard practice (Yescombe, Bodmer)
  sizes it as the SUM of the next N periods' debt service (e.g. next 6 months). Under that reading the
  target is [300+300, 300+100, 100, 0] = [600, 400, 100, 0], and:
  dsra_transfer_in [400, 0, 0, 0], dsra_release [0, 50, 300, 100], dsra_closing [450, 400, 100, 0].
  The two readings give different numbers from period 2, so this case does tell them apart.

## Notes — coverage (weak)
- The funding gate never bites. The only gate-0 period (P3) has zero shortfall, so top-up is 0 with or
  without the gate. A module that ignored the gate would pass. Suggest a gate-0 period with a shortfall,
  e.g. dsra_funding_gate = [1, 0, 1, 1] (P2 would then be 0 not 100 under the literal reading).
- The cash cap does fire (P1 and P2). Release fires (P3, P4). Last-period target 0 fires (P4).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
