# Golden answer: dsra_2

## Outputs (coordinator's ruling: target = SUM of the next two periods' debt service)
```python
dsra_target = [600, 400, 100, 0]
dsra_transfer_in = [400, 0, 0, 0]
dsra_release = [0, 50, 300, 100]
dsra_closing = [450, 400, 100, 0]
```

## Working
| Period | B/f | Next two DS | Target | Shortfall = max(target - b/f, 0) | Cash avail | Gate | Top-up | Release = max(b/f - target, 0) | Closing |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 50 | 300 + 300 | 600 | 550 | 400 | 1 | min(550, 400) x 1 = 400 | 0 | 450 |
| 2 | 450 | 300 + 100 | 400 | 0 | 100 | 0 | min(0, 100) x 0 = 0 | 50 | 400 |
| 3 | 400 | 100 | 100 | 0 | 400 | 1 | 0 | 300 | 100 |
| 4 | 100 | none | 0 | 0 | 400 | 1 | 0 | 100 | 0 |

## Notes — ambiguity
- None under the ruled (sum) target. The request's comment, "period 2 needs a top-up but the gate is
  shut", is only true under the old 2 x next-period reading (target 600). Under that reading:
  target [600, 600, 200, 0], transfer_in [400, 0, 0, 0], release [0, 0, 250, 200], closing [450, 450, 200, 0].

## Notes — coverage (still weak)
- The gate still never bites. Under the sum target, P2's b/f (450) already exceeds its target (400),
  so the shortfall is 0 and top-up is 0 with or without the gate. The outputs are identical to the
  sum-reading result of `dsra.md`, so this case adds nothing. A module that ignored the gate would pass.
- Fires: cash cap (P1), release (P2, P3, P4), last-period target 0 (P4). Not fired: gate-0 with a
  shortfall; an uncapped top-up (shortfall < cash).
- Suggested fix: cash_available_for_dsra = [200, 100, 400, 400], all else unchanged. Then
  P1 top-up min(550, 200) = 200, closing 250; P2 target 400, shortfall 150, gate 0, top-up 0
  (100 if the gate were ignored), closing 250; P3 target 100, release 150, closing 100; P4 release 100, closing 0.
  Expected: target [600, 400, 100, 0], transfer_in [200, 0, 0, 0], release [0, 0, 150, 100], closing [250, 250, 100, 0].

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
