# VBA module: specification and acceptance tests

**Status: specified, not built.** This is the macros' contract; they are done when acceptance tests V1 to V6
pass in Excel. Save as `excel/project_finance_model.xlsm`; export the module to
`excel/vba/ProjectFinance.bas` so Git can diff it. The `.xlsx` stays as the formula-only version.

## Why VBA here (each macro does something formulas cannot)

1. **ConvergeDebt** - the model is circular (debt <-> fee and IDC). The standard fix is a copy-paste loop, not Excel's
   iterative calculation, which hides non-convergence.
2. **RunGrid** - each grid point needs the whole model recalculated with different stress inputs.
3. **Breakeven** - a bisection with an explicit tolerance. Goal Seek stops at Excel's convergence setting (0.001 by
   default) and would not reconcile to Python at 1e-6.
4. **RunRegression** - runs `excel/regression/cases.csv` inside Excel, the Excel counterpart of the LibreOffice run.

## Procedures

| Procedure | Does | Rules |
|---|---|---|
| `ConvergeDebt()` | Repeats: copy `Checks!C5` to `Inputs!C32` and `Checks!C6` to `Inputs!C33` as values, `Application.Calculate`, until `Checks!B5` and `B6` are both TRUE. | Stop after 100 rounds with an error message naming the last change in debt. Report the number of rounds. |
| `RunGrid()` | For each revenue haircut in {0, 5, ..., 30%} and opex increase in {0, 10, ..., 40%}: write `Inputs!C26`, `C27`, recalculate, read `Analysis!C28`. Writes a sheet `Grid` and `excel/vba_grid.csv` (header `revenue_haircut,opex_increase,min_dscr`). | Save and restore `C26:C29`; set `C28` and `C29` to 0 during the run. |
| `Breakeven(level As Double) As Double` | Largest revenue haircut in [0, 1] keeping `Analysis!C28 >= level`, by bisection to 1e-12. | Same save/restore; other stresses 0. Return 0 if already below at 0. |
| `RunRegression()` | For every row of `cases.csv`: write the 25 inputs by column name (map from the header row), recalculate, log the 15 outputs to `excel/regression/vba_log.csv` as `case_id,field,actual,runner_pass`. | Numbers written with `Trim(Str(x))` (always a full stop); an error cell logs `#ERROR` and counts as a failure; restore inputs on exit, including after an error (`On Error GoTo Cleanup`). |

Cell map: `src/projectfinancelab/regression.py` (`INPUT_CELLS`, `OUTPUTS`). Switch off `ScreenUpdating` during loops.

## Acceptance tests

| # | Test | Pass condition |
|---|---|---|
| V1 | Set `Inputs!C11` (revenue year 1) to 60, run `ConvergeDebt` | Debt 355.658286 and uses 414.867916 (Python: 355.65828603142904, 414.8679157095831), both converged checks TRUE; then restore 62 and rerun |
| V2 | Set `Inputs!C20` (gearing) to 80%, run `ConvergeDebt` | Debt 331.075607, uses 413.844509, binding "gearing"; restore 90% |
| V3 | `RunGrid` | 35 rows; each within 1e-6 of `outputs/grid.csv` |
| V4 | `Breakeven(1)`, `Breakeven(1.05)`, `Breakeven(1.15)` | Within 1e-6 of the revenue rows of `outputs/breakevens.csv` |
| V5 | `RunRegression`, then `project-finance-lab verify-log --log excel/regression/vba_log.csv` | PASS, 510 of 510 |
| V6 | Mutation: change `Operations!D16` to `=D6*D12/1.3`, rerun `RunRegression`, then undo | Failures reported; verifier prints FAIL |

Record the Excel version and V5 output in the README when done.

## What you can claim once V1 to V6 pass

"Wrote VBA to resolve a debt-sizing circularity, run stress grids and bisection breakevens, and regression-test an Excel
project finance model against its Python implementation (510 checks)." Until then: Python and Excel formulas only.
