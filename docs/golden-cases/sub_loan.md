# Golden request: sub_loan (OMD M14)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods), balance brought forward in period 1 = opening_sub_loan:
- interest = rate x opening balance
- PIK = PIK share x interest (added to the balance); cash interest = interest - PIK
- balance before repayment = opening + drawdown + PIK
- repayment = min(repayment requested, balance before repayment)
- closing = balance before repayment - repayment

Inputs:
- sub_drawdown = [300, 0, 100, 0]
- sub_repayment_request = [0, 100, 0, 600]
- sub_interest_rate = 0.1
- sub_pik_share = 0.4
- opening_sub_loan = 100

Outputs wanted (4 values each): sub_interest, sub_interest_pik, sub_interest_cash, sub_repayment, sub_closing.
Source kind: hand-calculation (name the reviewer and the date).
