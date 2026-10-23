# Golden answer: tax_losses

## Outputs (literal reading: expire when age >= loss_life)
```python
tax_loss_used = [0, 100, 0, 50]
tax_loss_expired = [0, 80, 200, 0]
tax_loss_closing = [380, 200, 50, 0]
taxable_after_losses = [0, 0, 0, 350]
```

## Working (loss_life 2; opening 80 = pool of origin 0)
| Period | Pools at start (origin: amount, age) | (1) Expired | Profit | (2) Relieved, oldest first | (3) New pool | Pools at close | Closing | After losses |
|---|---|---|---|---|---|---|---|---|
| 1 | 0: 80 (age 1) | none -> 0 | -300 | none -> 0 | 1: 300 | 0: 80, 1: 300 | 380 | max(-300,0) - 0 = 0 |
| 2 | 0: 80 (age 2), 1: 300 (age 1) | pool 0 -> 80 | 100 | pool 1: 100 -> 100 | none | 1: 200 | 200 | 100 - 100 = 0 |
| 3 | 1: 200 (age 2) | pool 1 -> 200 | -50 | none -> 0 | 3: 50 | 3: 50 | 50 | 0 - 0 = 0 |
| 4 | 3: 50 (age 1) | none -> 0 | 400 | pool 3: 50 -> 50 | none | none | 0 | 400 - 50 = 350 |

## Ambiguity — marked ambiguous
- With "expire when age >= loss_life", a loss with loss_life 2 can be used in only ONE later period
  (age 1). Standard practice reads a "2-period carry-forward" as usable in the next 2 periods, so it
  expires when age > loss_life. The literal rule gives one fewer period of use than the name suggests.
- Alternative (expire when age > loss_life, i.e. age >= 3):

| Period | Expired | Relieved | Pools at close | Closing | After |
|---|---|---|---|---|---|
| 1 | 0 | 0 | 0: 80, 1: 300 | 380 | 0 |
| 2 | 0 (pool 0 age 2 survives) | pool 0: 80, pool 1: 20 -> 100 | 1: 280 | 280 | 0 |
| 3 | 0 (pool 1 age 2 survives) | 0 | 1: 280, 3: 50 | 330 | 0 |
| 4 | pool 1 age 3 -> 280 | pool 3: 50 -> 50 | none | 0 | 350 |

```python
# alternative
tax_loss_used = [0, 100, 0, 50]
tax_loss_expired = [0, 0, 0, 280]
tax_loss_closing = [380, 280, 330, 0]
taxable_after_losses = [0, 0, 0, 350]
```
- The builder should confirm which convention the spec intends before freezing the golden.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
