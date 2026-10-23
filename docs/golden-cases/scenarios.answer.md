# Golden answer: scenarios

## Outputs
Each output is one number, repeated on all 4 periods.
```python
live_multiplier__price = [1.05, 1.05, 1.05, 1.05]
live_multiplier__volume = [1.15, 1.15, 1.15, 1.15]
live_multiplier__capex = [0.9, 0.9, 0.9, 0.9]
live_scenario_result = [74.25, 74.25, 74.25, 74.25]
live_reconciliation = [-4.25, -4.25, -4.25, -4.25]
swing__price = [20, 20, 20, 20]
swing__volume = [26, 26, 26, 26]
swing__capex = [18, 18, 18, 18]
tornado_rank__price = [2, 2, 2, 2]
tornado_rank__volume = [1, 1, 1, 1]
tornado_rank__capex = [3, 3, 3, 3]
breakeven_multiplier__price = [0.6, 0.6, 0.6, 0.6]
breakeven_multiplier__volume = [0.6923076923076923] * 4  # = 9/13
breakeven_multiplier__capex = [1.4444444444444444] * 4  # = 13/9
```

## Working
**Live selection.** scenario_selector = 3 → upside (1-based: 1 base, 2 downside, 3 upside).
- price 1.05, volume 1.15, capex 0.9 (the upside multipliers).
- live_scenario_result = scenario_result__upside = 74.25.
- live_reconciliation = live_result - live_scenario_result = 70 - 74.25 = -4.25.

**Swings** = |result_up - result_down|.
| Driver | down | up | up - down | swing |
|---|---|---|---|---|
| price | 30 | 50 | +20 | 20 |
| volume | 27 | 53 | +26 | 26 |
| capex | 49 | 31 | -18 | 18 |

**Tornado rank** = 1 + count of other drivers with a strictly larger swing.
- volume (26): none larger → 1.
- price (20): volume larger → 1 + 1 = 2.
- capex (18): volume, price larger → 1 + 2 = 3.

**Breakeven** = 1 - base_result / slope; slope = (up - down) / (2 x 0.1) = (up - down) / 0.2.
- price: slope = 20 / 0.2 = 100 → 1 - 40/100 = 0.6.
- volume: slope = 26 / 0.2 = 130 → 1 - 40/130 = 1 - 4/13 = 9/13 = 0.692308.
- capex: slope = -18 / 0.2 = -90 → 1 - 40/(-90) = 1 + 4/9 = 13/9 = 1.444444.

Sense check: price at 0.6 → 40 + 100 x (0.6 - 1) = 0. Capex at 1.4444 → 40 - 90 x 0.4444 = 0. Holds.

## Notes — ambiguity / departure from practice
- **Breakeven anchor.** The rule anchors the line at (1.0, base_result), not at the midpoint of the
  down and up points. Here both agree: the midpoints are (30+50)/2 = 40, (27+53)/2 = 40, (49+31)/2 = 40,
  all equal to base_result. If the model is non-linear they will differ. Alternative (line through the
  two points only): breakeven = 1 - midpoint / slope. Same answers on these inputs.
- **Breakeven units.** Output is a multiplier, not a % change. Alternative (common in tornado reports):
  breakeven as a change from base = multiplier - 1 → price -40%, volume -30.77%, capex +44.44%.
- **No clamp.** A breakeven can be negative or very large (e.g. a near-flat driver). The rules do not clamp
  or flag it. Practice would flag a breakeven outside a plausible range as "not reachable".
- **Swing loses direction.** Capex has a negative slope; swing reports 18 with no sign. Tornado charts
  in practice keep the sign so the bar shows which side hurts. Rank is unaffected.
- **Rank ties.** "Strictly larger" gives competition ranking (1, 1, 3) on ties. That is standard.
- **Reconciliation not nil.** live_result 70 ≠ upside result 74.25. In practice this check should be 0
  when the live run uses the selected scenario's multipliers; -4.25 says the live run and the stored
  upside point differ. The rule just reports the gap, which is correct; the reader must treat a non-zero
  value as a flag.
- **Selector range.** No rule for a selector outside 1..3 (0, 4, non-integer). Undefined; should error.

## Notes — coverage (weak)
- Fired: selector = 3 (upside); positive and negative slopes; distinct swings, ranks 1/2/3; non-zero
  reconciliation.
- Not fired: selector = 1 and 2; swing = 0 → breakeven 0 branch; a tie in swings (strict-larger test).
- Variants: `scenarios_2.answer.md` (selector 2, zero swing, tie) and `scenarios_3.answer.md`
  (selector 1, reconciliation nil).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
