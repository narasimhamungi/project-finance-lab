# Test plan and results

`python -m pytest` runs everything below except the LibreOffice regression, which needs LibreOffice and is run by hand.

| Area | Test | File |
|---|---|---|
| Hand calculations | Debt, debt service, interest, balances, PLCR and distributions for a 3-year project solvable on paper; gearing-binding case; fee circularity D = 0.3(100 + 0.02D); IDC on the opening balance | `test_model.py` |
| Mechanics | Unlevered tax floor; delay hits year 1 only; capex overrun is equity-funded and leaves DSCR alone; lock-up traps cash until the tail; shortfalls recorded; IRR; invalid inputs rejected | `test_model.py` |
| Identities, any valid project (Hypothesis) | Debt = min(capacity, gearing x uses); balance at COD = debt; principal sums to debt; zero balance at maturity; sources = uses; sizing-case DSCR and LLCR equal the sculpting DSCR every year | `test_properties.py` |
| Frozen debt (Hypothesis) | A stress never changes the debt service; DSCR x debt service = CFADS; distributions = Σ(CFADS - debt service) + shortfalls | `test_properties.py` |
| Monotonicity (Hypothesis) | Minimum DSCR never rises as the revenue haircut or opex increase grows | `test_properties.py` |
| Breakevens | Hand case (20% revenue fall to 1.00x); the breakeven sits on the threshold and 1e-6 more stress breaks it; ordering across thresholds | `test_scenarios.py` |
| Workbook structure | Input cells labelled; outputs are formulas; **Construction and Operations never reference the stress cells**; no hard-coded numbers in time rows | `test_workbook.py` |
| Workbook values | 34 cases (the 4 shipped cases and 30 seeded random projects covering 1-3 construction years, both binding constraints, lock-up, default level, shortfalls, negative IRR) x 15 outputs, compared at 1e-6 | `excel/regression/` |
| Regression tooling | Committed cases are not stale; the verifier fails on missing, duplicated, unexpected or wrong rows | `test_regression.py` |

## Results (30 Sep 2026)

- pytest: 44 passed.
- LibreOffice regression: 510 of 510 checks pass. The first run found 4 failures: LibreOffice's IRR with its default
  starting guess returned no answer for projects whose equity IRR is negative. The workbook now tries a second guess
  (-10%); after the fix all 510 pass. The same run confirmed the tests catch problems: an early case description with a
  comma was caught by the no-quoting test, since a VBA reader splits on commas.
- Not yet run: the workbook in Excel (VBA harness, `docs/vba_spec.md`).
