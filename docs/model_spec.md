# Model specification

Written before the code and kept in step with it. Every formula below is implemented in
`src/projectfinancelab/model.py` and, cell for cell, in `excel/project_finance_model.xlsx`.
Inputs are hypothetical. This is not any rating agency's model, criteria or rating case.

## Timeline and units

Annual periods. Construction years t = 1..Nc (Nc ≤ 3), then operating years k = 1..No (No ≤ 30); operating year 1
starts at commercial operation (COD). Debt amortises over operating years 1..T, where T < No (a tail is required).
Amounts are in the units of the inputs; the example uses currency millions, nominal.

## Operations (any case)

| Item | Formula |
|---|---|
| Revenue | R_k = R_1 (1 + g_R)^(k-1) (1 - h), and in year 1 also x (1 - m/12) |
| Opex | O_k = O_1 (1 + g_O)^(k-1) (1 + o) |
| Depreciation | D_k = Capex / N_dep for k ≤ N_dep, else 0 |
| Tax | Tax_k = τ max(0, EBITDA_k - D_k) |
| CFADS | CFADS_k = EBITDA_k - Tax_k |

h = revenue haircut, o = opex increase, m = COD delay in months (0 to 12). The sponsor case has h = o = m = 0.

## Construction and funding

| Item | Formula |
|---|---|
| Capex | Capex_t = Capex x share_t |
| Fee | Fee_1 = f x Debt; 0 in later years |
| IDC | IDC_t = r x B_(t-1), capitalised (draws at year end; B_0 = 0) |
| Uses | U_t = Capex_t + Fee_t + IDC_t; U = Σ U_t |
| Debt share | s = Debt / U (pro-rata funding) |
| Draw, equity | Draw_t = s U_t; Equity_t = U_t - Draw_t; B_t = B_(t-1) + Draw_t |

## Sizing (sponsor case only)

- PV = Σ_(k=1..T) CFADS_k / (1 + r)^k, at the debt rate, at COD.
- Debt = min(PV / DSCR_target, gearing_max x U).
- **Circularity.** U depends on Debt through the fee and IDC, and Debt depends on U through the gearing cap.
  Python iterates (Debt, U) to a fixed point (tolerance 1e-12; the shipped case converges in 9 iterations).
  The workbook takes Debt and U as pasted values (Inputs C32:C33) and Checks confirms its own formulas return the same
  numbers. Excel's iterative calculation is not used because it hides non-convergence.
- Sculpting DSCR: DSCR* = PV / Debt (= DSCR_target when the DSCR constraint binds, higher when gearing binds).
- Debt service: DS_k = CFADS_k(sponsor) / DSCR*, k = 1..T. Interest_k = r B_(k-1); Principal_k = DS_k - Interest_k.
  Because the PV of DS at r equals Debt, the balance is exactly zero at maturity.
- **The schedule is then frozen.** Stresses never re-size it (tested in Python and structurally in the workbook:
  Construction and Operations cannot reference the stress cells).

## Analysis (any stress, frozen debt)

| Metric | Formula |
|---|---|
| DSCR_k | CFADS_k / DS_k, k ≤ T |
| LLCR_k | [Σ_(j=k..T) CFADS_j DF_j / DF_(k-1)] / B_(k-1), DF_j = (1 + r)^-j |
| PLCR at COD | Σ_(j=1..No) CFADS_j DF_j / Debt |
| Lock-up | DSCR_k < lock-up level: that year's cash is trapped |
| Default level | DSCR_k < default level: flagged (no acceleration modelled) |
| Cash | Avail_k = Cash_(k-1) + CFADS_k - DS_k; Shortfall_k = max(0, -Avail_k); Dist_k = 0 if locked else max(0, Avail_k); Cash_k = max(0, Avail_k) - Dist_k |
| Equity IRR | IRR of (-Equity_t, less the capex overrun in the last construction year; then Dist_k) |

Identity used as a test: on the sizing case, LLCR_k = DSCR_k = DSCR* for every k ≤ T, because both numerator and
denominator are PVs of the same flows at the same rate, scaled by DSCR*.

## Breakevens, grid and sensitivities

- Breakeven: the largest revenue haircut (on 0 to 100%) or opex increase (on 0 to 1,000%) at which the minimum DSCR
  stays at or above a threshold (1.00x, the default level, the lock-up level). Bisection to 1e-12, on the frozen debt.
- Grid: minimum DSCR over revenue haircut x opex increase, frozen debt.
- Interest-rate sensitivity: the debt is **re-sized** at each rate (a financing question, not a stress of existing debt).
