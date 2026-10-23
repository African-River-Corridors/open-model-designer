# Golden answer: fx_conversion

## Outputs
```python
fx_closing_rate = [0.072, 0.0684, 0.0684, 0.071136]
fx_period_rate = [0.076, 0.0702, 0.0684, 0.069768]
flow_reporting = [76.0, -28.08, 41.04, 17.442]
balance_closing_local = [1500, 1100, 1700, 1950]
balance_closing_reporting = [108.0, 75.24, 116.28, 138.7152]
fx_translation_difference = [-8.0, -4.68, 0.0, 4.9932]
```
All values are exact decimals. Compare at ~1e-12 absolute: binary floats give e.g. 0.07200000000000001,
and the P3 translation difference may come out as about -7.1e-15 rather than exactly 0.

## Working
| P | Open rate | Dep | Close rate = open x (1 - d) | Period rate = avg | Flow LCU | Flow USD | Open bal LCU | Close bal LCU | Close bal USD | Open bal x open rate | Translation diff |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.08 | 0.10 | 0.08 x 0.90 = 0.072 | 0.076 | 1000 | 76.00 | 500 | 1500 | 1500 x 0.072 = 108.00 | 40.00 | 108 - 40 - 76 = -8.00 |
| 2 | 0.072 | 0.05 | 0.072 x 0.95 = 0.0684 | 0.0702 | -400 | -28.08 | 1500 | 1100 | 1100 x 0.0684 = 75.24 | 108.00 | 75.24 - 108 + 28.08 = -4.68 |
| 3 | 0.0684 | 0.00 | 0.0684 | 0.0684 | 600 | 41.04 | 1100 | 1700 | 1700 x 0.0684 = 116.28 | 75.24 | 116.28 - 75.24 - 41.04 = 0.00 |
| 4 | 0.0684 | -0.04 | 0.0684 x 1.04 = 0.071136 | 0.069768 | 250 | 17.442 | 1700 | 1950 | 1950 x 0.071136 = 138.7152 | 116.28 | 138.7152 - 116.28 - 17.442 = 4.9932 |

Cross-check: translation difference = open bal LCU x (close - open rate) + flow LCU x (close - period rate).
- P1: 500 x (-0.008) + 1000 x (-0.004) = -4 - 4 = -8. Holds.
- P2: 1500 x (-0.0036) + (-400) x (-0.0018) = -5.4 + 0.72 = -4.68. Holds.
- P4: 1700 x 0.002736 + 250 x 0.001368 = 4.6512 + 0.342 = 4.9932. Holds.

## Roll-forward check (requested)
Closing USD = 500 x 0.08 + cumulative flow USD + cumulative translation difference:
| P | 40 + cum flow USD | + cum TD | = | Closing USD |
|---|---|---|---|---|
| 1 | 40 + 76 = 116 | -8 | 108.00 | 108.00 |
| 2 | 116 - 28.08 = 87.92 | -12.68 | 75.24 | 75.24 |
| 3 | 87.92 + 41.04 = 128.96 | -12.68 | 116.28 | 116.28 |
| 4 | 128.96 + 17.442 = 146.402 | -7.6868 | 138.7152 | 138.7152 |
Holds in every period.

## Notes — ambiguity
- None material. The rules match IAS 21 practice: flows at the average rate, balances at the closing
  rate, the difference to a translation reserve.
- Convention note: "closing = opening x (1 - d)" is a linear depreciation of the USD/LCU rate. Some models
  define depreciation on the inverse quote (LCU per USD rises by d, so closing = opening / (1 + d)). Under
  that alternative: closing rates [0.0727273, 0.0692641, 0.0692641, 0.0721501]. The request is explicit, so
  the literal reading above is the golden.
- Period rate is the arithmetic mean of opening and closing; a geometric mean or a monthly-average rate
  would differ slightly. The rule is explicit.

## Notes — coverage (done)
- Fired: depreciation (P1, P2), zero change (P3, translation difference exactly 0), appreciation via a
  negative input (P4, positive translation difference); positive and negative flows; roll-forward
  identity in every period. No floors, caps or flags in the rules, so no branch is left unfired.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
