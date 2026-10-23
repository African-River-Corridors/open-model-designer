# Golden request: cover_ratios, second case (OMD M10)

Why: the first golden case cannot tell LLCR from PLCR (loan life equals project life), fires no
zero-denominator branch, and its period-4 inputs disagree. This case is internally consistent (debt
closing follows from a 6% rate, opening 1000 and the stated debt service), has a loan life shorter than
the project life, and a repaid loan. Same rules as `cover_ratios.md`.

Inputs:
- cfads = [400, 380, 360, 340]
- debt_service = [250, 250, 645.116, 0]
- debt_closing = [810, 608.6, 0, 0]
- loan_life_flag = [1, 1, 1, 0]
- discount_rate = 0.06
- opening_debt = 1000

(consistency: 1000 x 1.06 - 250 = 810; 810 x 1.06 - 250 = 608.6; 608.6 x 1.06 = 645.116 clears the loan)

Notes for the reviewer: debt at the start of period 4 is 0, so LLCR and PLCR read 0 there; DSCR in
period 4 is 0 (debt service 0). LLCR counts CFADS only in periods with loan_life_flag = 1; PLCR counts all.

Outputs wanted (4 values each): dscr, dscr_rolling, llcr, plcr.
Source kind: hand-calculation (name the reviewer and the date).
