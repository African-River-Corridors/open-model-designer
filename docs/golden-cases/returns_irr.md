# Golden case returns_irr_4 — request (brief as given)

Independent reviewer, golden case calculated from first principles. No code repository read.
Same definitions as returns_irr_1, but 4 periods.

Periods dated 0, 365, 730, 1095 days (whole days; years = days / 365):
- Project flows: -1000, 800, 800, -500
- Equity flows: -300, 200, 260, -120

Inputs: project discount rate 0.08/year; equity discount rate 0.12/year; days per year 365; IRR guess 0.10.

Definitions:
1. NPV at rate r = sum over flows of flow / (1 + r)^(years since the first flow). The first flow is not discounted.
2. The IRRs of a series are all rates r in the range (-0.99, 10] at which that NPV is zero. Find every one, to at least 8 significant figures.
3. The reported IRR is the IRR nearest the guess (0.10).
4. Sign changes: walk the flows in order, ignoring zero flows, and count how many times the sign differs from the previous non-zero flow.
5. The IRR is unique (flag 1) if the sign-change count is exactly 1, else 0.
6. Cumulative equity cash flow per period = running sum of the equity flows.
7. Equity payback period = if the final cumulative equity cash flow is >= 0, then (the number of periods whose cumulative is < 0) + 1; otherwise 0.

Report, for each of project and equity: every IRR found, the reported IRR, the NPV at its discount rate, the sign-change count and the unique flag; then the 4 cumulative equity values and the payback period, each to at least 12 significant figures. Also report the NPV at each reported IRR (should be ~0) as a self-check.
