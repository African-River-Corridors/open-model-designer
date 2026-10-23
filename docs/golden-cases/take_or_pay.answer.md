# Golden answer: take_or_pay

## Outputs
```python
sales_revenue = [6000, 4000, 5000, 0]
shortfall_volume = [0, 20, 0, 100]
shortfall_payment = [0.0, 800.0, 0.0, 4000.0]
revenue = [6000.0, 4800.0, 5000.0, 4000.0]
```

## Working (unit price 50, shortfall share 0.8)
| P | Min | Delivered | Sales = Del x 50 | Shortfall = max(Min - Del, 0) | Payment = SF x 50 x 0.8 | Revenue |
|---|---|---|---|---|---|---|
| 1 | 100 | 120 | 6000 | max(-20, 0) = 0 | 0 | 6000 |
| 2 | 100 | 80 | 4000 | 20 | 20 x 40 = 800 | 4800 |
| 3 | 100 | 100 | 5000 | max(0, 0) = 0 | 0 | 5000 |
| 4 | 100 | 0 | 0 | 100 | 100 x 40 = 4000 | 4000 |
Totals: sales 15,000; shortfall payment 4,800; revenue 19,800.

## Notes — ambiguity / departure from practice
- **Test period.** The rule tests the minimum every period with no carry-over. Most take-or-pay offtake
  contracts test an annual (contract-year) minimum, so excess delivery in one quarter offsets a shortfall in
  another. If these four periods are one contract year: minimum 400, delivered 300, shortfall 100, payment
  100 x 40 = 4,000 (versus 4,800 per period). The 800 gap is P1's 20 units of excess, which the per-period
  rule does not credit against P2's 20 units of shortfall.
- **Make-up rights.** Standard take-or-pay usually lets the buyer take paid-for-but-undelivered volume
  later without paying again (a make-up bank). The rules have none. If a make-up bank applied, P2's 20 paid
  units could be recovered later, reducing future sales revenue. Not computed: the request gives no
  make-up terms.
- **Share below 100%.** A shortfall share of 0.8 behaves like a deficiency payment (pay a share of price),
  not a full take-or-pay. Fine as an input, but worth naming in the module doc.

## Notes — coverage (done)
- Fired: the max(…, 0) floor (P1, delivery above the minimum); the boundary at exactly the minimum (P3);
  a partial shortfall (P2); zero delivery (P4, revenue is the shortfall payment alone).
  Every branch fires.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
