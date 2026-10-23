# Golden answer: cash_sweep_target_leverage_2

## Outputs
```python
sweep_amount = [250, 100, 0, 0]
debt_after_sweep = [750, 800, 800, 500]
cash_after_sweep = [150, 0, 600, 600]
```

## Working (target leverage 2.5)
| Period | Cash avail | Debt before | EBITDA | 2.5 x EBITDA | Excess debt = max(debt - 2.5 x EBITDA, 0) | Amount = min(excess, cash) | Flag | Sweep | Debt after | Cash after |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 400 | 1000 | 300 | 750 | 250 | min(250, 400) = 250 | 1 | 250 | 750 | 150 |
| 2 | 100 | 900 | 300 | 750 | 150 | min(150, 100) = 100 | 1 | 100 | 800 | 0 |
| 3 | 600 | 800 | 320 | 800 | 0 | 0 | 1 | 0 | 800 | 600 |
| 4 | 600 | 500 | 340 | 850 | max(-350, 0) = 0 | 0 | 1 | 0 | 500 | 600 |

## Notes — ambiguity
- None in the stated rules. 2.5 x 320 = 800.0 exactly in floating point, so P3's excess is exactly 0.
  Practice note: leverage tests usually use LTM EBITDA; here EBITDA is a per-period input.

## Notes — coverage (still weak, one branch)
- Fixed: debt-excess cap binds cleanly below cash (P1); cash cap binds (P2); excess exactly 0 (P3);
  zero floor bites in a flagged period (P4: a module without the floor gives -350, debt 850, cash 950).
- Not fired: the flag. Every flag is 1, so a module that ignored sweep_flag would pass. Case 1 does not
  rescue it either: its only flag-0 period (P4) has amount 0 anyway. Across both cases, the flag is never tested.
- Suggested fix: add a fifth period, or reuse P1 with flag 0 in a separate case: cash 400, debt 1000,
  EBITDA 300, flag 0 (expect sweep 0, debt 1000, cash 400; ignoring the flag gives 250).

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
