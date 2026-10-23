# Golden request: debt_repay_annuity (OMD M9)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods): interest = rate x opening balance (paid every period); principal is repaid only
where the repayment flag is 1 and never exceeds the opening balance; closing = opening - principal;
debt service = interest + principal. Opening balance in period 1 = opening_debt.
Principal (when flagged) = level payment - interest, where level payment = opening_debt x r / (1 - (1 + r)^(-n)),
r = interest_rate, n = repayment_periods.

Inputs: repayment_flag = [1, 1, 1, 1]; interest_rate = 0.06; opening_debt = 2000; repayment_periods = 5
(note: the flag covers 4 of the 5 periods, so a balance remains at the end)
Outputs wanted (4 values each): interest, debt_repayment, debt_service, debt_closing.
Source kind: hand-calculation (name the reviewer and the date).
