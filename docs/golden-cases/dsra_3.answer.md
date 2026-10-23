# Golden answer: dsra_3

## Inputs (dsra_2 with cash changed; same rules as `dsra.md`)
- debt_service = [0, 300, 300, 100]
- cash_available_for_dsra = [200, 100, 400, 400]
- dsra_funding_gate = [1, 0, 1, 1]
- opening_dsra = 50
- target = SUM of the next two periods' debt service (coordinator's ruling; fewer at the end; last period 0)
- top-up = min(max(target - b/f, 0), cash) x gate; release = max(b/f - target, 0); closing = b/f + top-up - release

## Outputs
```python
dsra_target = [600, 400, 100, 0]
dsra_transfer_in = [200, 0, 0, 0]
dsra_release = [0, 0, 150, 100]
dsra_closing = [250, 250, 100, 0]
```

## Working
| Period | B/f | Next two DS | Target | Shortfall | Cash | Gate | Top-up | Release | Closing |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 50 | 300 + 300 | 600 | 550 | 200 | 1 | min(550, 200) x 1 = 200 | 0 | 250 |
| 2 | 250 | 300 + 100 | 400 | 150 | 100 | 0 | min(150, 100) x 0 = 0 | 0 | 250 |
| 3 | 250 | 100 | 100 | 0 | 400 | 1 | 0 | 150 | 100 |
| 4 | 100 | none | 0 | 0 | 400 | 1 | 0 | 100 | 0 |

## Gate check — confirmed, the gate bites in period 2
A module that ignored the gate would give P2 top-up min(150, 100) = 100, closing 350; then P3 release 250,
closing 100; P4 release 100, closing 0. So transfer_in [200, 100, 0, 0], release [0, 0, 250, 100],
closing [250, 350, 100, 0]. This differs from the correct result in P2 and P3.

## Notes — ambiguity
- None under the ruled sum target.

## Notes — coverage
- Fired: gate 0 with a shortfall (P2); cash cap (P1, and P2 before the gate); release (P3, P4);
  last-period target 0 (P4); a period with neither top-up nor release (P2).
- Not fired: an uncapped top-up (shortfall < cash, gate 1). The cash cap always binds when a top-up
  happens, so a module that always paid the full cash available would pass. Minor; a later case could
  set P1 cash = 600 (expect top-up 550, not 600).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
