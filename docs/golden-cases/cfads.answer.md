# Golden answer: cfads

## Outputs
```python
cfads_pre_tax = [330, 540, 780, 600]
cfads = [330, 500, 680, 530]
```

## Working
| P | Revenue | Opex | WC movement | CFADS pre-tax = Rev - Opex - WC mvmt | Tax paid | CFADS |
|---|---|---|---|---|---|---|
| 1 | 800 | 350 | +120 (uses cash) | 800 - 350 - 120 = 330 | 0 | 330 |
| 2 | 1000 | 400 | +60 | 1000 - 400 - 60 = 540 | 40 | 500 |
| 3 | 1200 | 450 | -30 (release) | 1200 - 450 + 30 = 780 | 100 | 680 |
| 4 | 900 | 380 | -80 (release) | 900 - 380 + 80 = 600 | 70 | 530 |
Totals: pre-tax 2250; CFADS 2040; tax 210. 2250 - 210 = 2040. Holds.

## Notes — ambiguity / departure from practice
- None in the stated rules. Sign convention is explicit (positive movement uses cash).
- Practice note: the standard CFADS definition (Yescombe; Bodmer) also deducts maintenance capex and
  movements in non-debt reserves (e.g. a MRA), and tax is the tax actually paid in the period. This module
  has no capex or reserve ports, so if those are meant to be inside CFADS they must be netted upstream.
  Worth stating in the module doc.

## Notes — coverage (done)
- Fired: WC movement that uses cash (P1, P2) and one that releases cash (P3, P4); tax at 0 (P1) and
  positive (P2–P4). No floors, caps or flags in the rules. A negative CFADS is not exercised, but the
  rules have no branch for it (no floor), so this is not a coverage gap.

Source kind: hand-calculation — reviewer: an independent reviewer agent that did not see the code, 2026-10-23
