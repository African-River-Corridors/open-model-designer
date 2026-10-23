# Golden request: tax_losses (OMD M3, open-model-designer PR for #25)

Needed: expected outputs by **hand calculation by a reviewer other than the builder**. Do not use the
module's code. Send numbers and working back to the builder.

Rules (4 periods, losses by period of origin):
- Each period, in order: (1) a pool whose age (period number minus its origin period) is at least
  `loss_life` expires whole, before relief; (2) profit before losses (if positive) is relieved against
  the pools, oldest first; (3) a loss made this period (negative profit) forms a new pool, usable from
  the next period.
- Brought-forward losses (`opening_losses`) are the oldest pool, origin period 0.
- profit after losses = max(profit, 0) - losses relieved.

Inputs:
- taxable_profit_pre_loss = [-300, 100, -50, 400]
- loss_life = 2
- opening_losses = 80

Outputs wanted (4 values each): tax_loss_used, tax_loss_expired, tax_loss_closing, taxable_after_losses.
Source kind: hand-calculation (name the reviewer and the date).
