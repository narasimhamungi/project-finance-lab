# Hypothetical contracted operating asset (illustrative inputs, not market terms or any real project)

*Hypothetical inputs for illustration. Not a real project, not market terms, not advice, and not any rating agency's model, criteria or rating case.*

Units: currency millions, nominal, annual periods.

## Sizing (sponsor case)

- Uses 415.45 (capex 400.00, IDC 9.90, fee 5.54); debt 369.54 (88.9% gearing); equity 45.91
- Debt capacity at 1.35x target DSCR 369.54; gearing cap 373.90; binding constraint: DSCR; sculpting DSCR 1.35x
- Debt and uses solved as a fixed point in 9 iterations; repayment schedule then frozen

## Cases on the frozen debt

| Case | Min DSCR | Avg DSCR | LLCR at COD | PLCR at COD | Lock-up yrs | Default-level yrs | Shortfall | Equity IRR |
|---|---|---|---|---|---|---|---|---|
| sponsor | 1.35x | 1.35x | 1.35x | 1.64x | 0 | 0 | 0.00 | 23.7% |
| base | 1.25x | 1.25x | 1.25x | 1.52x | 0 | 0 | 0.00 | 19.0% |
| downside | 1.10x | 1.10x | 1.11x | 1.33x | 18 | 0 | 0.00 | 8.3% |
| delay_6m | 0.56x | 1.31x | 1.29x | 1.58x | 1 | 1 | 13.37 | 20.9% |

## Breakevens on the frozen debt (one lever at a time)

| Lever | Threshold | Largest stress before the minimum DSCR falls below it |
|---|---|---|
| revenue_haircut | DSCR 1.00x (payment) (1.00x) | 21.56% |
| revenue_haircut | default-level DSCR (1.05x) | 18.48% |
| revenue_haircut | lock-up DSCR (1.15x) | 12.32% |
| opex_increase | DSCR 1.00x (payment) (1.00x) | 87.84% |
| opex_increase | default-level DSCR (1.05x) | 75.29% |
| opex_increase | lock-up DSCR (1.15x) | 50.20% |

## Interest-rate sizing sensitivity (debt re-sized)

| Debt rate | Debt | Gearing | Binding | Sculpting DSCR | Sponsor equity IRR |
|---|---|---|---|---|---|
| 5.00% | 372.55 | 90.0% | gearing | 1.45x | 29.4% |
| 6.00% | 369.54 | 88.9% | DSCR | 1.35x | 23.7% |
| 7.00% | 341.96 | 82.2% | DSCR | 1.35x | 16.5% |

Full tables: cases.csv, breakevens.csv, grid.csv (minimum DSCR by revenue haircut and opex increase), sizing_sensitivity.csv, debt_schedule.csv.
