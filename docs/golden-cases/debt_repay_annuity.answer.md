# Golden answer: debt_repay_annuity

## Outputs
```python
interest = [120.0, 98.71243194825726, 76.14760981340996, 52.22889835047182]
debt_repayment = [354.79280086237895, 376.08036891412166, 398.64519104896897, 422.56390251190714]
debt_service = [474.79280086237895, 474.79280086237895, 474.79280086237895, 474.79280086237895]
debt_closing = [1645.207199137621, 1269.1268302234994, 870.4816391745304, 447.91773666262327]
```
Rounded: interest [120.00, 98.71, 76.15, 52.23]; principal [354.79, 376.08, 398.65, 422.56];
service 474.79 each period; closing [1645.21, 1269.13, 870.48, 447.92].

## Working (r = 0.06, n = 5, opening 2000)
Level payment = 2000 x 0.06 / (1 - 1.06^-5) = 120 / 0.252742 = 474.7928009.
| Period | Opening | Interest = 0.06 x opening | Principal = 474.7928 - interest | Debt service | Closing |
|---|---|---|---|---|---|
| 1 | 2000.0000 | 120.0000 | 354.7928 | 474.7928 | 1645.2072 |
| 2 | 1645.2072 | 98.7124 | 376.0804 | 474.7928 | 1269.1268 |
| 3 | 1269.1268 | 76.1476 | 398.6452 | 474.7928 | 870.4816 |
| 4 | 870.4816 | 52.2289 | 422.5639 | 474.7928 | 447.9177 |
Check: closing after 4 periods should equal the PV of the one remaining payment = 474.7928 / 1.06 =
447.9177. It does. Principal grows by a factor of 1.06 each period (354.79 x 1.06 = 376.08), as it should.

## Notes
- Rule is clear and standard (mortgage-style annuity). The residual 447.92 is intended (the request says so).
- Interest is on the actual opening balance each period, and the cap "never exceeds opening" never binds here.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
