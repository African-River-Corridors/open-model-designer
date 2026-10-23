# Golden request: lockup (OMD M12)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods):
- lock-up flag = 1 if DSCR < lock-up threshold AND debt outstanding flag = 1, else 0
- default flag = 1 if DSCR < default threshold AND debt outstanding flag = 1, else 0
- distributions permitted = 1 - lock-up flag
(a DSCR exactly equal to the threshold passes)

Inputs:
- dscr = [1.6, 1.25, 1.15, 0.95]
- debt_outstanding_flag = [1, 1, 1, 1]
- lockup_dscr = 1.3
- default_dscr = 1.1

Outputs wanted (4 values each): lockup_flag, default_flag, distributions_permitted_flag.
Source kind: hand-calculation (name the reviewer and the date).
