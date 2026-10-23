# Golden request: three_statements (OMD M22)

Needed: expected outputs by hand calculation by a reviewer other than the builder. Do not use the
module's code. Send numbers and working back. 4 periods. The opening balance sheet balances (assets 1230 = liabilities and equity 1230).

Rules, per period:
- EBITDA = revenue - operating cost; EBIT = EBITDA - depreciation; profit before tax = EBIT - interest; net income = profit before tax - tax charge
- cash from operations = net income + depreciation - working capital movement + tax charge - tax paid
- cash from investing = - capital additions
- cash from financing = debt drawn - debt repaid + equity contributed - dividends
- net cash flow = the three added; cash closing = cash opening + net cash flow (period 1 opens at opening_cash)
- tax payable closing = opening + tax charge - tax paid
- share capital closing = opening + equity contributed
- retained earnings closing = opening + net income - dividends
- total assets = cash closing + fixed assets net book value (fa_nbv_closing) + working capital (working_capital)
- total liabilities and equity = debt_closing + tax payable + share capital + retained earnings
- balance difference = total assets - total liabilities and equity (the inputs fa_nbv_closing, working_capital, debt_closing are supplied and consistent with their flows; a nonzero difference would be a finding)

Inputs:
- opening_cash = 150, opening_fixed_assets = 1000, opening_working_capital = 80, opening_debt = 600,
  opening_tax_payable = 20, opening_share_capital = 400, opening_retained_earnings = 210
- revenue = [800, 900, 1000, 1100]
- operating_cost = [400, 430, 450, 470]
- depreciation = [100, 100, 100, 100]
- interest = [60, 52, 44, 36]
- tax_charge = [48, 64, 80, 96]
- tax_paid = [20, 56, 72, 88]
- capital_additions = [200, 50, 0, 0]
- working_capital_movement = [20, 10, 10, -5]
- debt_drawdown = [100, 0, 0, 0]
- debt_repayment = [40, 80, 80, 100]
- equity_contribution = [0, 50, 0, 0]
- dividends = [0, 60, 120, 160]
- fa_nbv_closing = [1100, 1050, 950, 850]
- working_capital = [100, 110, 120, 115]
- debt_closing = [660, 580, 500, 400]

Outputs wanted (4 values each): ebitda, ebit, profit_before_tax, net_income, cash_from_operations, cash_from_investing,
cash_from_financing, net_cash_flow, cash_closing, tax_payable_closing, share_capital_closing, retained_earnings_closing,
total_assets, total_liabilities_equity, balance_difference.
Source kind: hand-calculation (name the reviewer and the date).
