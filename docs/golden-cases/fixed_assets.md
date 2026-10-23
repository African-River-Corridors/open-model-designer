# Golden request: fixed_assets (OMD M1, open-model-designer PR for #23)

Needed: expected outputs by **hand calculation by a reviewer other than the builder**. Do not use the
module's code. Send numbers and working back to the builder.

Rules, per period (4 periods):
- gross cost carried = gross brought forward + additions (first period: `opening_gross`)
- NBV before depreciation = gross carried - accumulated depreciation brought forward
- depreciation = share in use x min(gross carried / useful life, NBV before depreciation)
- accumulated depreciation carried = brought forward + depreciation
- NBV = gross carried - accumulated depreciation carried

Inputs:
- capital_additions = [2000, 300, 0, 800]
- use_fraction = [0, 0.5, 1, 1]
- useful_life = 5
- opening_gross = 0
- opening_accum_depreciation = 0

Outputs wanted (4 values each): depreciation, fa_gross_closing, fa_accum_depreciation_closing,
fa_nbv_closing.
Source kind: hand-calculation (name the reviewer and the date).
