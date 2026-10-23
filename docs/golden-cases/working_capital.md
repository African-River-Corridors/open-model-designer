# Golden request: working_capital (OMD M16)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back.

Rules, per period (4 periods):
- receivables = revenue x receivable_days / days_in_period
- payables = operating_cost x payable_days / days_in_period
- cash buffer = operating_cost x cash_buffer_days / days_in_period   (counted as an asset)
- working capital = receivables + cash buffer - payables
- movement = working capital - prior period's working capital; the first period's prior value is opening_working_capital.
  A positive movement uses cash.

Inputs:
- revenue = [900, 1200, 1500, 1000]
- operating_cost = [540, 600, 720, 500]
- receivable_days = 30
- payable_days = 45
- cash_buffer_days = 10
- days_in_period = 90
- opening_working_capital = 50

Outputs wanted (4 values each): receivables, payables, cash_buffer, working_capital, working_capital_movement.
Source kind: hand-calculation (name the reviewer and the date).
