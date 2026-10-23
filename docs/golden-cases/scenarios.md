# Golden request: scenarios (OMD M23)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back. Three drivers (price, volume, capex), three scenarios
(base, downside, upside). The per-point results are inputs (they come from running a model once per point).

Rules (every output is one number; the module repeats it on each of the 4 periods):
- live multiplier of a driver = the multiplier of the selected scenario (scenario_selector is 1-based: 1 base, 2 downside, 3 upside)
- live_scenario_result = scenario_result of the selected scenario
- live_reconciliation = live_result - live_scenario_result
- swing of a driver = |result_up - result_down|
- tornado rank of a driver = 1 + the number of other drivers with a strictly larger swing
- breakeven multiplier of a driver = 0 if its swing is 0, else 1 - base_result / slope, where slope = (result_up - result_down) / (2 x sensitivity_step)
  (the multiplier at which the result is nil on the straight line through the up and down points)

Inputs:
- scenario_selector = 3
- sensitivity_step = 0.1
- base_result = 40
- multiplier__price__base = 1.0, multiplier__volume__base = 1.0, multiplier__capex__base = 1.0
- multiplier__price__downside = 0.85, multiplier__volume__downside = 0.9, multiplier__capex__downside = 1.25
- multiplier__price__upside = 1.05, multiplier__volume__upside = 1.15, multiplier__capex__upside = 0.9
- scenario_result__base = 40, scenario_result__downside = -9, scenario_result__upside = 74.25
- result_down__price = 30, result_up__price = 50
- result_down__volume = 27, result_up__volume = 53
- result_down__capex = 49, result_up__capex = 31
- live_result = 70

Outputs wanted (one number each): live_multiplier__price, live_multiplier__volume, live_multiplier__capex,
live_scenario_result, live_reconciliation, swing__price, swing__volume, swing__capex,
tornado_rank__price, tornado_rank__volume, tornado_rank__capex,
breakeven_multiplier__price, breakeven_multiplier__volume, breakeven_multiplier__capex.
Source kind: hand-calculation (name the reviewer and the date).
