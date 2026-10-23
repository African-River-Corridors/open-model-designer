# Golden answer: idc

## Outputs
```python
idc_capitalised = [2.2670025188916876, 9.102272078371158, 18.30784797879994, 25.38554845203117]
debt_closing = [302.2670025188917, 911.3692745972628, 1529.6771225760626, 1855.0626710280937]
capital_additions_incl_idc = [
    452.2670025188917,
    909.1022720783711,
    918.3078479787999,
    475.3855484520312,
]
```
Rounded: IDC [2.2670, 9.1023, 18.3078, 25.3855]; closing [302.2670, 911.3693, 1529.6771, 1855.0627];
additions incl. IDC [452.2670, 909.1023, 918.3078, 475.3855]. Total IDC 55.0627.

## Working — closed form (rate 0.015, weight 0.5, so 1 - w x r = 0.9925)
| Period | Opening | Draw | Base = open + 0.5 x draw | IDC = 0.015 x base / 0.9925 | Closing = open + draw + IDC | Cap adds | Cap adds + IDC |
|---|---|---|---|---|---|---|---|
| 1 | 0 | 300 | 150 | 2.2670025 | 302.2670025 | 450 | 452.2670025 |
| 2 | 302.2670025 | 600 | 602.2670025 | 9.1022721 | 911.3692746 | 900 | 909.1022721 |
| 3 | 911.3692746 | 600 | 1211.3692746 | 18.3078480 | 1529.6771226 | 900 | 918.3078480 |
| 4 | 1529.6771226 | 300 | 1679.6771226 | 25.3855485 | 1855.0626710 | 450 | 475.3855485 |

## Working — iteration by hand (IDC_k+1 = 0.015 x (open + 0.5 x (draw + IDC_k)), IDC_0 = 0)
Each step adds 0.0075 x IDC_k to the non-circular base, so it converges fast (factor 0.0075 per step).
| Period | Iter 1 (IDC_0 = 0) | Iter 2 | Iter 3 | Iter 4 | Closed form |
|---|---|---|---|---|---|
| 1 | 2.250000 | 2.266875 | 2.267002 | 2.267003 | 2.2670025 |
| 2 | 9.034005 | 9.101760 | 9.102268 | 9.102272 | 9.1022721 |
| 3 | 18.170539 | 18.306818 | 18.307840 | 18.307848 | 18.3078480 |
| 4 | 25.195157 | 25.384121 | 25.385538 | 25.385549 | 25.3855485 |
Iteration and closed form agree to 1e-6 after four steps.

## Notes
- Rule is clear and standard (interest on opening plus half the period's draw and roll-up, IDC rolled into
  the loan). Closed form is the exact fixed point of the circularity.
- Alternative for reference (no circularity, IDC on opening + 0.5 x draw only):
  IDC [2.25, 9.03375, 18.16925625, 25.19179509375], closing [302.25, 911.28375, 1529.45300625, 1854.64480134375].
  The gap (total 0.42) is the size a test must be able to see: use a tolerance well below 0.01.
- Closing debt includes IDC, but the draw does not. So IDC is a non-cash roll-up on top of the
  facility draw. If the facility limit must also cover IDC, that check lives in debt_draw, not here.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
