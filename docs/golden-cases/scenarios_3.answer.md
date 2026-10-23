# Golden answer: scenarios_3 (variant — selector 1, base)

## Inputs (full)
- scenario_selector = 1
- sensitivity_step = 0.1
- base_result = 40
- multiplier__price__base = 1.0, multiplier__volume__base = 1.0, multiplier__capex__base = 1.0
- multiplier__price__downside = 0.85, multiplier__volume__downside = 0.9, multiplier__capex__downside = 1.25
- multiplier__price__upside = 1.05, multiplier__volume__upside = 1.15, multiplier__capex__upside = 0.9
- scenario_result__base = 40, scenario_result__downside = -9, scenario_result__upside = 74.25
- result_down__price = 30, result_up__price = 50
- result_down__volume = 27, result_up__volume = 53
- result_down__capex = 49, result_up__capex = 31
- live_result = 40

## Outputs
Each output is one number, repeated on all 4 periods.
```python
live_multiplier__price = [1.0, 1.0, 1.0, 1.0]
live_multiplier__volume = [1.0, 1.0, 1.0, 1.0]
live_multiplier__capex = [1.0, 1.0, 1.0, 1.0]
live_scenario_result = [40, 40, 40, 40]
live_reconciliation = [0, 0, 0, 0]
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
- selector 1 → base: all multipliers 1.0; live_scenario_result = 40.
- live_reconciliation = 40 - 40 = 0 (the expected clean state).
- Swings, ranks and breakevens are independent of the selector; working as in `scenarios.answer.md`
  (price 20/0.2 = 100 → 0.6; volume 26/0.2 = 130 → 9/13; capex -18/0.2 = -90 → 13/9).

## Notes
- Ambiguity notes as in `scenarios.answer.md`.
- Coverage: fires selector 1 and a nil reconciliation. Guards that swing/rank/breakeven do not depend on the
  selector.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
