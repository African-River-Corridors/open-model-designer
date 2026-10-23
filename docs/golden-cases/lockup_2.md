# Golden request: lockup, stronger second case (OMD M12)

Why: in the first case the debt flag is 1 in every period and no DSCR sits exactly on a threshold, so a
module that ignored the debt flag, or got "equal passes" wrong, would pass. Same rules as `lockup.md`.

Inputs (4 periods):
- dscr = [1.30, 1.10, 0.95, 0.95]
- debt_outstanding_flag = [1, 1, 1, 0]
- lockup_dscr = 1.3
- default_dscr = 1.1

Expected to be tested: period 1 (DSCR exactly 1.3: lock-up 0), period 2 (exactly 1.1: lock-up 1, default 0),
period 3 (below both: 1, 1), period 4 (below both but no debt outstanding: 0, 0, permitted 1).

Outputs wanted (4 values each): lockup_flag, default_flag, distributions_permitted_flag.
Source kind: hand-calculation (name the reviewer and the date).
