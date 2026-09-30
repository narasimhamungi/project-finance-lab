# Changelog

## 0.1.0 - 2026-09-30
- Model spec, assumptions register, test plan and limitations written first.
- Python model: sponsor-case sizing (DSCR and gearing constraints, debt-uses fixed point), sculpted and frozen schedule,
  stressed analysis (DSCR, LLCR, PLCR, lock-up, default level, shortfalls, equity IRR), breakevens, grid, rate sensitivity.
- Formula workbook reproducing the model; 34-case LibreOffice regression (510 checks).
- Regression finding fixed: the workbook's equity IRR returned nothing for negative-IRR cases with the default starting
  guess; it now tries a second guess.
- VBA module specified with acceptance tests; not built.
