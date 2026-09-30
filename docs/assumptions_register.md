# Assumptions register

Every input in `examples/project_hypothetical.json` is hypothetical: chosen to be internally plausible for a contracted
operating asset, not taken from a real project, term sheet or market survey.

| # | Assumption | Value | Why this value / effect | Status |
|---|---|---|---|---|
| A1 | Construction | 2 years, capex 400 split 45/55 | Simple two-year build | Hypothetical |
| A2 | Operations | 25 years | Tail of 7 years after an 18-year tenor | Hypothetical |
| A3 | Revenue | 62 in year 1, +2% a year | Contracted, indexed revenue | Hypothetical |
| A4 | Opex | 14 in year 1, +2.5% a year | Opex grows faster than revenue: margins erode slowly | Hypothetical |
| A5 | Tax | 25% of EBITDA - depreciation, floor 0; depreciation straight line over 20 years | Unlevered: ignores the interest deduction (conservative) and losses carried forward | Simplification |
| A6 | Debt rate | 6.00% all-in, fixed for the whole life | Assumes a full hedge; no floating exposure | Simplification |
| A7 | Tenor | 18 operating years | Leaves a tail, needed so trapped cash is released | Hypothetical |
| A8 | Target DSCR | 1.35x | Binds in the sponsor case | Hypothetical |
| A9 | Maximum gearing | 90% of total uses | Does not bind at 6% (it does at 5%) | Hypothetical |
| A10 | Upfront fee | 1.5% of debt, construction year 1 | Creates the debt-uses circularity | Hypothetical |
| A11 | Lock-up / default-level DSCR | 1.15x / 1.05x | Covenant-style tests; no cure or acceleration mechanics | Hypothetical |
| A12 | Funding | Pro-rata debt and equity; IDC on opening balance, capitalised | Simplest standard convention | Simplification |
| A13 | Stress cases | base: revenue -5%, opex +5%; downside: revenue -12%, opex +15%, capex overrun 5%; delay: 6 months. Named "downside", not "rating case", so nothing implies an agency's criteria | Illustrative layering only. Not any agency's base or rating case | Hypothetical |
| A14 | COD delay | Revenue lost in operating year 1; debt service unchanged; no delay liquidated damages, no reserve account | Shows the gross exposure a reserve or LDs would cover | Simplification |
