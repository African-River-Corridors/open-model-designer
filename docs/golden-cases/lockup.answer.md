# Golden answer: lockup

## Outputs
```python
lockup_flag = [0, 1, 1, 1]
default_flag = [0, 0, 0, 1]
distributions_permitted_flag = [1, 0, 0, 0]
```

## Working (lock-up 1.3, default 1.1; equal passes)
| Period | DSCR | Debt flag | DSCR < 1.3? | Lock-up | DSCR < 1.1? | Default | Distributions permitted = 1 - lock-up |
|---|---|---|---|---|---|---|---|
| 1 | 1.60 | 1 | no | 0 | no | 0 | 1 |
| 2 | 1.25 | 1 | yes | 1 | no | 0 | 0 |
| 3 | 1.15 | 1 | yes | 1 | no | 0 | 0 |
| 4 | 0.95 | 1 | yes | 1 | yes | 1 | 0 |

## Notes — ambiguity
- None in the stated rules. Practice note: lock-up is often tested on a historic or rolling-average DSCR,
  not the period DSCR; that is an input choice, outside this module.

## Notes — coverage (weak)
- debt_outstanding_flag is 1 in every period, so the AND branch never fires. A module that ignored the
  debt flag would pass. Suggest a final period with flag 0 and DSCR below both thresholds (expect 0, 0, 1).
- No DSCR sits exactly on a threshold, though the request states "equal passes". A strict-vs-non-strict
  bug would pass. Suggest a period with DSCR = 1.3 (expect lock-up 0) and one with DSCR = 1.1
  (expect lock-up 1, default 0).
- P2 and P3 give the same outputs, so they test the same thing.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
