# Golden request: debt_repay_linear (OMD M9)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods): interest = rate x opening balance (paid every period); principal is repaid only
where the repayment flag is 1 and never exceeds the opening balance; closing = opening - principal;
debt service = interest + principal. Opening balance in period 1 = opening_debt.
Principal (when flagged) = opening_debt / (number of flagged periods), so the loan is cleared over the flagged periods.

Inputs: repayment_flag = [1, 1, 1, 0]; interest_rate = 0.04; opening_debt = 1200
Outputs wanted (4 values each): interest, debt_repayment, debt_service, debt_closing.
Source kind: hand-calculation (name the reviewer and the date).
