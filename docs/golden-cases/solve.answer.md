# Golden answer: solve (OMD solver, issue #35)

## Outputs
```python
value = 100 / 40.000001  # 2.4999993750000156, both cases, to within 1e-12
case_a_bracket_after_growth = (1.0, 4.0)  # no growth
case_b_bracket_after_growth = (2.0, 4.0)  # grown twice
case_a_evaluations = 63  # f(hi), f(lo), 60 halvings, final f(hi)
case_b_evaluations = 65  # f(1), f(2), f(4), f(lo), 60 halvings, final f(hi)
```

## Working
f(x) <= tol means 100 / x - 40 <= 1e-6, so 100 / x <= 40.000001, so x >= 100 / 40.000001.
The smallest such x is the closed-form root at the tolerance: 100 / 40.000001 = 2.49999937500...
(The root at zero is 2.5. The tolerance moves it down by 6.25e-7.)

Case A. f(4) = 25 - 40 = -15 <= tol, so there is no growth. f(1) = 60 > tol, so the bracket holds the threshold.
Sixty halvings shrink the width 3 to 3 / 2^60, about 2.6e-18, below the spacing of floats near 2.5.
So the value equals the root to float precision.

Case B. f(1) = 60 > tol: bracket becomes (1, 2). f(2) = 10 > tol: bracket becomes (2, 4).
f(4) = -15 <= tol, so growth stops. f(2) = 10 > tol, so the bracket holds the threshold.
Then 60 halvings on width 2 give the same root.

Evaluation counts: Case A calls f at hi, lo, 60 midpoints and the final hi: 1 + 1 + 60 + 1 = 63.
Case B calls f at 1, 2 and 4 during growth, then lo, 60 midpoints and the final hi: 3 + 1 + 60 + 1 = 65.
