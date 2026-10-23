# Golden answer: scenarios_2 (variant — selector 2, zero swing, tied swings)

## Inputs (full)
- scenario_selector = 2
- sensitivity_step = 0.1
- base_result = 40
- multiplier__price__base = 1.0, multiplier__volume__base = 1.0, multiplier__capex__base = 1.0
- multiplier__price__downside = 0.85, multiplier__volume__downside = 0.9, multiplier__capex__downside = 1.25
- multiplier__price__upside = 1.05, multiplier__volume__upside = 1.15, multiplier__capex__upside = 0.9
- scenario_result__base = 40, scenario_result__downside = -9, scenario_result__upside = 74.25
- result_down__price = 40, result_up__price = 40
- result_down__volume = 30, result_up__volume = 50
- result_down__capex = 50, result_up__capex = 30
- live_result = -5

## Outputs
Each output is one number, repeated on all 4 periods.
```python
live_multiplier__price = [0.85, 0.85, 0.85, 0.85]
live_multiplier__volume = [0.9, 0.9, 0.9, 0.9]
live_multiplier__capex = [1.25, 1.25, 1.25, 1.25]
live_scenario_result = [-9, -9, -9, -9]
live_reconciliation = [4, 4, 4, 4]
swing__price = [0, 0, 0, 0]
swing__volume = [20, 20, 20, 20]
swing__capex = [20, 20, 20, 20]
tornado_rank__price = [3, 3, 3, 3]
tornado_rank__volume = [1, 1, 1, 1]
tornado_rank__capex = [1, 1, 1, 1]
breakeven_multiplier__price = [0, 0, 0, 0]
breakeven_multiplier__volume = [0.6, 0.6, 0.6, 0.6]
breakeven_multiplier__capex = [1.4, 1.4, 1.4, 1.4]
```

## Working
**Live selection.** selector 2 → downside: price 0.85, volume 0.9, capex 1.25.
live_scenario_result = -9. live_reconciliation = -5 - (-9) = 4.

**Swings.** price |40 - 40| = 0; volume |50 - 30| = 20; capex |30 - 50| = 20.

**Ranks** (1 + count strictly larger):
- volume 20: capex 20 is not strictly larger, price 0 is not → 1.
- capex 20: same → 1.
- price 0: volume and capex larger → 1 + 2 = 3.

**Breakeven.**
- price: swing 0 → 0 (zero-swing branch; slope would be 0 and the formula would divide by zero).
- volume: slope = 20 / 0.2 = 100 → 1 - 40/100 = 0.6.
- capex: slope = -20 / 0.2 = -100 → 1 - 40/(-100) = 1.4.

## Notes — ambiguity / departure from practice
- **Zero-swing sentinel.** 0 is also a valid breakeven value in principle (result nil at multiplier 0).
  A reader cannot tell "no sensitivity" from "breaks even at zero". Alternative: return NaN/None or a
  separate flag. Literal reading gives 0.
- **Tie ranking.** Competition ranking gives 1, 1, 3 — no rank 2. Dense ranking would give 1, 1, 2.
  The rule as written gives 1, 1, 3.
- Other notes as in `scenarios.answer.md`.

## Notes — coverage (done, with scenarios.answer.md and scenarios_3.answer.md)
- Fired here: selector 2; swing = 0 → breakeven 0; tie in swings; positive and negative slopes;
  positive reconciliation.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
