# project-finance-lab

![CI](https://github.com/narasimhamungi/project-finance-lab/actions/workflows/ci.yml/badge.svg)

A cash-flow model of a project financing: senior debt sized on the sponsor case, repayments sculpted to a target DSCR,
and then **frozen** while operating stresses are run against it. Built twice, in Python and in Excel formulas, and
reconciled across 34 input sets.

> The inputs in `examples/` are **hypothetical**: not a real project, not market terms, not advice. The stress cases
> are an illustrative layering, **not any rating agency's base case, rating case, model or criteria**.

## Status

- [x] Model specification, assumptions register, test plan, limitations and changelog, written before the code:
      [`docs/`](docs/)
- [x] Sizing: debt = min(PV of CFADS over the tenor / target DSCR, gearing cap x total uses), with the debt-uses
      circularity (upfront fee, capitalised IDC) solved as a fixed point
- [x] Sculpted repayment schedule, frozen before any stress; metrics DSCR, LLCR, PLCR, equity IRR; lock-up and
      default-level tests; payment shortfalls
- [x] Breakevens by bisection (revenue and opex, against 1.00x, the default level and the lock-up level), a stress
      grid, and an interest-rate sizing sensitivity
- [x] Tests and CI: 44 pytest tests, including Hypothesis property tests of the identities for any valid project
- [x] Excel workbook reproducing the model in formulas: [`excel/project_finance_model.xlsx`](excel/project_finance_model.xlsx)
- [x] Workbook regression: 34 cases x 15 outputs; LibreOffice 24.2 passes 510 of 510 checks at 1e-6
      ([`excel/regression/`](excel/regression/)). It caught that the workbook's equity IRR returned nothing for
      negative-IRR cases; the workbook now tries a second starting guess
- [ ] VBA (circularity loop, stress grid, bisection breakeven, regression harness in Excel): specified with acceptance
      tests in [`docs/vba_spec.md`](docs/vba_spec.md), not built

## Findings on the example

| Case (hypothetical) | Min DSCR | LLCR at COD | Lock-up years | Payment shortfall | Equity IRR |
|---|---|---|---|---|---|
| Sponsor | 1.35x | 1.35x | 0 | 0.00 | 23.7% |
| Base: revenue -5%, opex +5% | 1.25x | 1.25x | 0 | 0.00 | 19.0% |
| Downside: revenue -12%, opex +15%, capex overrun 5% | 1.10x | 1.11x | 18 | 0.00 | 8.3% |
| COD delay of 6 months | 0.56x | 1.29x | 1 | 13.37 | 20.9% |

- On the frozen debt, revenue can fall **21.6%** before the minimum DSCR reaches 1.00x, 18.5% to the default level
  and 12.3% to lock-up. Opex has far more room (87.8% to 1.00x), because opex is under a quarter of revenue.
- The downside case never pays a distribution during the tenor but never misses debt service: the equity absorbs
  the stress.
- A 6-month delay does more damage to year-1 coverage than the downside case does to any year. With no reserve
  account or delay damages in the model, it produces a shortfall: that is the gap those protections exist to cover.
- Sizing: at 6% the DSCR constraint binds (88.9% gearing). At 5% the gearing cap binds instead, and the sculpting DSCR
  rises to 1.45x: cheaper debt does not raise proceeds beyond the cap.

Full output: [`outputs/summary.md`](outputs/summary.md) and CSVs.

## Design choices worth checking

- **Frozen debt.** If sizing read the stressed cash flows, every stressed DSCR would equal the target by construction
  and every breakeven would be meaningless. Python keeps sizing and analysis as separate functions; a property test
  checks that no stress changes the debt service; in the workbook a test checks that no formula on the sizing sheets
  refers to a stress cell.
- **Circularity.** Solved by iteration in Python; in Excel, pasted values with convergence checks rather than Excel's
  iterative calculation (which hides non-convergence).
- **Identity tests.** On the sizing case, LLCR equals the sculpting DSCR in every year. Reconciling Python to Excel
  cannot catch an error both share; identities can.

## Run

```bash
pip install -e ".[test]"
python -m pytest
project-finance-lab run --config examples/project_hypothetical.json --out outputs
python excel/build_workbook.py                   # rebuild the workbook (needs openpyxl)
project-finance-lab regression-cases             # rebuild excel/regression/cases.csv after any model change
python excel/regression/run_libreoffice.py       # evaluate the workbook on every case (needs LibreOffice)
project-finance-lab verify-log --log excel/regression/libreoffice_log.csv
```

## Layout

| Path | What |
|---|---|
| `src/projectfinancelab/model.py` | Operations, sizing and the frozen schedule, stressed analysis, IRR |
| `src/projectfinancelab/scenarios.py` | Cases, breakevens, grid, rate sensitivity |
| `src/projectfinancelab/regression.py` | Workbook cell map, regression cases, log verifier |
| `excel/` | Workbook, its builder, and the regression cases, LibreOffice runner and log |
| `docs/model_spec.md` | Every formula |
| `docs/assumptions_register.md`, `docs/limitations.md`, `docs/test_plan.md`, `docs/vba_spec.md` | As named |
