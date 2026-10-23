# Golden request: dsra, stronger second case (OMD M11)

Why: in the first case the funding gate never bites (its only gate-0 period has no shortfall), so a module
that ignored the gate would pass. Same rules as `dsra.md` (target = sum of the next two periods' debt service).

Inputs:
- debt_service = [0, 300, 300, 100]
- cash_available_for_dsra = [400, 100, 400, 400]
- dsra_funding_gate = [1, 0, 1, 1]      # period 2 needs a top-up but the gate is shut
- opening_dsra = 50

Outputs wanted (4 values each): dsra_target, dsra_transfer_in, dsra_release, dsra_closing.
Source kind: hand-calculation (name the reviewer and the date).
