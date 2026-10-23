# Golden answer: debt_draw

## Outputs
```python
debt_drawdown = [250, 350, 150, 0]
funding_gap = [0, 0, 150, 150]
debt_closing = [300, 650, 800, 800]
```

## Working (facility limit 800, opening debt 50)
| Period | Opening | Headroom = 800 - opening | Need | Flag | Need x flag | Drawdown = min | Gap = need - draw | Closing |
|---|---|---|---|---|---|---|---|---|
| 1 | 50 | 750 | 250 | 1 | 250 | 250 | 0 | 300 |
| 2 | 300 | 500 | 350 | 1 | 350 | 350 | 0 | 650 |
| 3 | 650 | 150 | 300 | 1 | 300 | 150 (cap binds) | 150 | 800 |
| 4 | 800 | 0 | 150 | 0 | 0 | 0 | 150 | 800 |

## Notes
- Literal reading is clear. Period 4 gap = 150: the gap is need less draw, whatever the reason the draw is
  zero (flag off and no headroom both apply). If the builder meant the gap to count only need while the
  facility is available (need x flag - draw), period 4 would be 0. The literal rule (150) is the safer
  one: an unmet need is shown, not hidden.
- Opening debt of 50 counts against the limit, so total drawn is capped at 800 including it.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
