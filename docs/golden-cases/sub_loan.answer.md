# Golden answer: sub_loan

## Outputs
```python
sub_interest = [10.0, 40.4, 32.016, 43.29664]
sub_interest_pik = [4.0, 16.16, 12.8064, 17.318656]
sub_interest_cash = [6.0, 24.24, 19.2096, 25.977984]
sub_repayment = [0.0, 100.0, 0.0, 450.285056]
sub_closing = [404.0, 320.16, 432.9664, 0.0]
```
(Floats will differ in the last bits, e.g. 40.400000000000006; compare with a tolerance of 1e-9.)

## Working (rate 0.1, PIK share 0.4, opening 100)
| Period | Opening | Interest = 0.1 x opening | PIK = 0.4 x int | Cash int | Drawdown | Before repay = open + draw + PIK | Request | Repay = min(request, before) | Closing |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 100 | 10 | 4 | 6 | 300 | 404 | 0 | 0 | 404 |
| 2 | 404 | 40.4 | 16.16 | 24.24 | 0 | 420.16 | 100 | 100 | 320.16 |
| 3 | 320.16 | 32.016 | 12.8064 | 19.2096 | 100 | 432.9664 | 0 | 0 | 432.9664 |
| 4 | 432.9664 | 43.29664 | 17.318656 | 25.977984 | 0 | 450.285056 | 600 | 450.285056 | 0 |

## Notes — ambiguity
- Interest runs on the opening balance only. In-period drawdowns earn no interest until next period
  (P1's 300 draw earns nothing in P1). That matches end-of-period drawdown timing. If drawdowns are
  start-of-period, interest would be on opening + drawdown: P1 interest 40, not 10. The stated rule is
  clear, so the literal reading stands; flag only if the model's timing convention differs.
- Repayment is not limited by cash available here; that cap belongs to the waterfall.

## Notes — coverage
- Good: drawdown, PIK capitalisation, a part repayment and the balance cap (P4: request 600 > 450.29)
  all fire. Non-round figures from P2 on test compounding of PIK.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
