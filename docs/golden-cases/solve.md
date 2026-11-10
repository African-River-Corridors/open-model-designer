# Golden request: solve (OMD solver, issue #35)

Needed: expected outputs by hand calculation from a closed-form root. Do not use the solver's code.

Rule. `omd.solve.bisect_threshold` finds the smallest x with f(x) <= tol, for an f that does not increase with x.

Function: f(x) = 100 / x - 40. Tolerance: tol = 1e-6. Steps: 60.

Case A. Bracket lo = 1, hi = 4. The bracket holds the threshold, so hi does not grow.
Case B. Bracket lo = 0.5, hi = 1. f(1) and f(2) are above tol, so hi must grow (grow = 2) before it holds.

Outputs wanted for each case: value (the smallest x with f(x) <= tol), the final lo and hi of the growth
step (the bracket before the halvings), and the evaluation count. Source kind: hand-calculation.
