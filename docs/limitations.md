# Limitations

- **Hypothetical inputs.** The example is not a real project, term sheet or market survey. The stress cases are an
  illustrative layering and are not any rating agency's base case, rating case or criteria. Nothing here is a rating.
- **Annual periods.** Real financings run semi-annual or quarterly with sculpting and covenant tests per period.
- **No reserve accounts** (DSRA, maintenance reserve) and no delay liquidated damages. That is why a 6-month delay produces
  a payment shortfall in the example: the result shows the gross exposure a reserve or LDs would have to cover.
- **Unlevered tax** (no interest deduction, no loss carry-forward), and depreciation on capex only (not IDC or fees).
- **Fixed all-in rate** for construction and operations; no hedge breakage, floating tranche, or refinancing.
- **Shortfalls are recorded, not resolved.** No sponsor support, no acceleration, no cure mechanics.
- **Single senior tranche**, pro-rata funding, no standby facilities or equity bridge.
- **Workbook verification.** The workbook passes 510 of 510 regression checks in LibreOffice 24.2. The Excel run is the VBA
  harness in `docs/vba_spec.md`, which is specified, not built. LibreOffice's IRR needed a second starting guess for
  negative-IRR cases; whether Excel's does is one of the things the Excel run will show.
