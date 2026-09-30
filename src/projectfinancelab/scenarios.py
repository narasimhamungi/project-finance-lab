"""Cases, breakevens, stress grid and sizing sensitivities, all on top of model.py.

Operating stresses (cases, grid, breakevens) run against the debt frozen at sponsor-case sizing.
Sizing sensitivities (interest rate) re-size the debt: they answer "how much debt would this project raise",
a different question from "how much stress can the debt as sized absorb".
"""
from __future__ import annotations

from dataclasses import replace

from .model import Financing, ProjectInputs, Stress, analyse, size_debt


def run_cases(p: ProjectInputs, fin: Financing, cases: dict[str, Stress]) -> list[dict]:
    rows = []
    for name, s in cases.items():
        a = analyse(p, fin, s)
        rows.append({"case": name, "revenue_haircut": s.revenue_haircut, "opex_increase": s.opex_increase,
                     "delay_months": s.delay_months, "capex_overrun": s.capex_overrun, "min_dscr": a.min_dscr,
                     "avg_dscr": a.avg_dscr, "llcr_cod": a.llcr_cod, "min_llcr": a.min_llcr, "plcr_cod": a.plcr_cod,
                     "lockup_years": a.lockup_years, "default_level_years": a.default_years,
                     "total_shortfall": a.total_shortfall, "equity_irr": a.equity_irr})
    return rows


def _bisect(ok, hi: float, tol: float = 1e-12) -> float:
    """Largest x in [0, hi] with ok(x) True, assuming ok is True then False as x rises."""
    if not ok(0.0):
        return 0.0
    if ok(hi):
        return hi
    lo = 0.0
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


def breakeven(p: ProjectInputs, fin: Financing, lever: str, level: float = 1.0) -> float:
    """Largest stress on one lever keeping the minimum DSCR at or above `level`, on the frozen debt.
    lever: "revenue_haircut" (searched on 0-1) or "opex_increase" (searched on 0-10, i.e. up to +1,000%)."""
    hi = {"revenue_haircut": 1.0, "opex_increase": 10.0}[lever]
    return _bisect(lambda x: analyse(p, fin, Stress(**{lever: x})).min_dscr >= level, hi)


def breakevens(p: ProjectInputs, fin: Financing) -> list[dict]:
    rows = []
    for lever in ("revenue_haircut", "opex_increase"):
        for label, level in (("DSCR 1.00x (payment)", 1.0), ("default-level DSCR", p.default_dscr),
                             ("lock-up DSCR", p.lockup_dscr)):
            rows.append({"lever": lever, "threshold": label, "dscr_level": level,
                         "breakeven": breakeven(p, fin, lever, level)})
    return rows


def grid(p: ProjectInputs, fin: Financing, haircuts: list[float], increases: list[float]) -> list[dict]:
    return [{"revenue_haircut": h, "opex_increase": o,
             "min_dscr": analyse(p, fin, Stress(revenue_haircut=h, opex_increase=o)).min_dscr}
            for h in haircuts for o in increases]


def sizing_sensitivity(p: ProjectInputs, rate_shifts: list[float]) -> list[dict]:
    rows = []
    for shift in rate_shifts:
        q = replace(p, debt_rate=p.debt_rate + shift)
        f = size_debt(q)
        rows.append({"debt_rate": q.debt_rate, "debt": f.debt, "gearing": f.debt / f.total_uses,
                     "binding": f.binding, "sculpt_dscr": f.sculpt_dscr,
                     "sponsor_equity_irr": analyse(q, f).equity_irr})
    return rows
