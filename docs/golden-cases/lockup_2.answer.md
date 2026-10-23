# Golden answer: lockup_2

## Outputs
```python
lockup_flag = [0, 1, 1, 0]
default_flag = [0, 0, 1, 0]
distributions_permitted_flag = [1, 0, 0, 1]
```

## Working (lock-up 1.3, default 1.1; equal passes)
| Period | DSCR | Debt flag | DSCR < 1.3? | Lock-up | DSCR < 1.1? | Default | Distributions permitted = 1 - lock-up |
|---|---|---|---|---|---|---|---|
| 1 | 1.30 | 1 | no (equal passes) | 0 | no | 0 | 1 |
| 2 | 1.10 | 1 | yes | 1 | no (equal passes) | 0 | 0 |
| 3 | 0.95 | 1 | yes | 1 | yes | 1 | 0 |
| 4 | 0.95 | 0 | yes, but no debt | 0 | yes, but no debt | 0 | 1 |

## Notes — ambiguity
- None. Floating-point check: the literals 1.30 and 1.3 are the same double, as are 1.10 and 1.1, so
  equality holds exactly. If the module ever receives a computed DSCR, a value like 1.2999999999 would
  lock up; that is an input-precision matter, outside this case.

## Notes — coverage (done)
- Equal-to-lock-up passes (P1). Equal-to-default passes default but fails lock-up (P2). Below both (P3).
  Debt flag 0 overrides both (P4). P3 vs P4 differ only in the debt flag, so the AND branch is isolated.
- Every branch fires. A strict/non-strict bug fails P1 or P2; ignoring the debt flag fails P4.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
