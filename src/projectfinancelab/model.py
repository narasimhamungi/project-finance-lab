"""Project finance cash-flow model: DSCR-sculpted senior debt, sized once and then frozen.

Annual periods. Construction years 1..Nc, then operating years 1..No (operating year 1 starts at COD).
All inputs are the user's; the shipped example is hypothetical. This is not any rating agency's model.

Two stages, kept apart on purpose:
1. size_debt(p): sponsor case only. Debt = min(PV of CFADS over the tenor / target DSCR, gearing cap x uses).
   Uses include interest during construction (IDC) and an upfront fee, which depend on the debt, so debt and
   uses are solved as a fixed point. Repayments are sculpted to the resulting DSCR and then FROZEN.
2. analyse(p, fin, stress): applies a stress to operating cash flows against the frozen debt schedule. If a stress
   re-sized the debt, every stressed DSCR would equal the sculpting DSCR by construction and breakevens would be
   meaningless; tests guard against that.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MAX_CONSTRUCTION, MAX_OPERATION = 3, 30        # workbook layout limits


@dataclass(frozen=True)
class ProjectInputs:
    construction_years: int
    capex: float                      # total, before IDC and fees
    capex_profile: tuple[float, ...]  # share of capex per construction year; sums to 1
    operation_years: int
    revenue_y1: float
    revenue_growth: float
    opex_y1: float
    opex_growth: float
    tax_rate: float                   # on EBITDA - depreciation, floored at 0 (unlevered; see limitations)
    depreciation_years: int           # straight line on capex from COD
    debt_rate: float                  # all-in fixed (hedged) rate, construction and operations
    debt_tenor: int                   # operating years of amortisation; must leave a tail
    target_dscr: float
    max_gearing: float                # debt / total uses
    upfront_fee: float                # share of debt, paid in construction year 1
    lockup_dscr: float                # distributions blocked in a year whose DSCR is below this
    default_dscr: float               # DSCR below this is flagged as a default-level event

    def __post_init__(self):
        if not 1 <= self.construction_years <= MAX_CONSTRUCTION:
            raise ValueError(f"construction_years must be 1..{MAX_CONSTRUCTION}")
        if len(self.capex_profile) != self.construction_years or abs(sum(self.capex_profile) - 1) > 1e-9 \
                or min(self.capex_profile) < 0:
            raise ValueError("capex_profile: one non-negative share per construction year, summing to 1")
        if not 1 <= self.debt_tenor < self.operation_years <= MAX_OPERATION:
            raise ValueError(f"need 1 <= debt_tenor < operation_years <= {MAX_OPERATION} (a tail is required)")
        if self.capex <= 0 or self.revenue_y1 <= 0 or self.opex_y1 < 0:
            raise ValueError("capex and revenue must be positive, opex non-negative")
        if not (0 <= self.tax_rate < 1 and 0 < self.debt_rate < 1 and 0 < self.max_gearing < 1
                and 0 <= self.upfront_fee < 0.1 and self.depreciation_years >= 1):
            raise ValueError("rate, gearing, fee or depreciation input out of range")
        if not 1 <= self.default_dscr <= self.lockup_dscr <= self.target_dscr:
            raise ValueError("need 1 <= default_dscr <= lockup_dscr <= target_dscr")

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectInputs":
        return cls(**{**d, "capex_profile": tuple(d["capex_profile"])})


@dataclass(frozen=True)
class Stress:
    revenue_haircut: float = 0.0      # share of revenue lost in every operating year
    opex_increase: float = 0.0        # proportional increase in opex
    delay_months: float = 0.0         # COD delay: revenue lost in operating year 1 only (0-12); no LDs assumed
    capex_overrun: float = 0.0        # share of capex, funded by sponsor equity in the last construction year

    def __post_init__(self):
        if not (0 <= self.revenue_haircut <= 1 and self.opex_increase >= 0 and 0 <= self.delay_months <= 12
                and self.capex_overrun >= 0):
            raise ValueError("stress out of range")


NO_STRESS = Stress()


@dataclass(frozen=True)
class Operations:
    revenue: list[float]
    opex: list[float]
    ebitda: list[float]
    depreciation: list[float]
    tax: list[float]
    cfads: list[float]


def operations(p: ProjectInputs, s: Stress = NO_STRESS) -> Operations:
    rev, opx, ebitda, dep, tax, cfads = [], [], [], [], [], []
    for k in range(1, p.operation_years + 1):
        r = p.revenue_y1 * (1 + p.revenue_growth) ** (k - 1) * (1 - s.revenue_haircut)
        if k == 1:
            r *= 1 - s.delay_months / 12
        o = p.opex_y1 * (1 + p.opex_growth) ** (k - 1) * (1 + s.opex_increase)
        d = p.capex / p.depreciation_years if k <= p.depreciation_years else 0.0
        e = r - o
        t = p.tax_rate * max(0.0, e - d)
        rev.append(r); opx.append(o); ebitda.append(e); dep.append(d); tax.append(t); cfads.append(e - t)
    return Operations(rev, opx, ebitda, dep, tax, cfads)


def discount_factors(rate: float, n: int) -> list[float]:
    """DF_k = 1 / (1 + rate)^k for k = 1..n, measured from COD."""
    return [(1 + rate) ** -k for k in range(1, n + 1)]


@dataclass(frozen=True)
class Financing:
    debt: float
    total_uses: float
    debt_share: float
    pv_cfads: float                   # PV at COD of sponsor-case CFADS over the tenor, at the debt rate
    debt_dscr_capacity: float
    debt_gearing_cap: float
    binding: str                      # "DSCR" or "gearing"
    sculpt_dscr: float                # = pv_cfads / debt; equals target_dscr when DSCR binds
    iterations: int
    capex: list[float]                # construction years
    fee: list[float]
    idc: list[float]
    uses: list[float]
    debt_draw: list[float]
    equity: list[float]
    debt_service: list[float]         # tenor years: the frozen schedule
    opening_balance: list[float]
    interest: list[float]
    principal: list[float]
    closing_balance: list[float]
    sponsor_cfads: list[float] = field(repr=False)


def _construction(p: ProjectInputs, debt: float, uses_guess: float):
    """Pro-rata funding at debt share = debt / uses_guess. IDC is charged on the opening balance
    (draws at year end) and capitalised; the fee is paid in construction year 1."""
    share = debt / uses_guess
    bal, rows = 0.0, []
    for t in range(p.construction_years):
        capex = p.capex * p.capex_profile[t]
        fee = p.upfront_fee * debt if t == 0 else 0.0
        idc = p.debt_rate * bal
        uses = capex + fee + idc
        draw = share * uses
        bal += draw
        rows.append((capex, fee, idc, uses, draw, uses - draw))
    return share, rows


def size_debt(p: ProjectInputs, tol: float = 1e-12, max_iter: int = 500) -> Financing:
    cf = operations(p).cfads
    df = discount_factors(p.debt_rate, p.debt_tenor)
    pv = sum(c * d for c, d in zip(cf[:p.debt_tenor], df))
    if min(cf[:p.debt_tenor]) <= 0:
        raise ValueError("sponsor-case CFADS must be positive in every tenor year to sculpt debt service")
    cap_dscr = pv / p.target_dscr
    uses = p.capex
    debt = min(cap_dscr, p.max_gearing * uses)
    for it in range(1, max_iter + 1):
        _, rows = _construction(p, debt, uses)
        new_uses = sum(r[3] for r in rows)
        new_debt = min(cap_dscr, p.max_gearing * new_uses)
        done = abs(new_uses - uses) < tol and abs(new_debt - debt) < tol
        uses, debt = new_uses, new_debt
        if done:
            break
    else:
        raise RuntimeError("debt sizing did not converge")
    share, rows = _construction(p, debt, uses)
    capex, fee, idc, u, draw, eq = (list(x) for x in zip(*rows))
    sculpt = pv / debt
    ds = [c / sculpt for c in cf[:p.debt_tenor]]
    opening, interest, principal, closing = [], [], [], []
    bal = sum(draw)
    for k in range(p.debt_tenor):
        i = p.debt_rate * bal
        opening.append(bal); interest.append(i); principal.append(ds[k] - i)
        bal -= ds[k] - i
        closing.append(bal)
    gear_cap = p.max_gearing * uses
    return Financing(debt=debt, total_uses=uses, debt_share=share, pv_cfads=pv, debt_dscr_capacity=cap_dscr,
                     debt_gearing_cap=gear_cap, binding="DSCR" if cap_dscr <= gear_cap else "gearing",
                     sculpt_dscr=sculpt, iterations=it, capex=capex, fee=fee, idc=idc, uses=u, debt_draw=draw,
                     equity=eq, debt_service=ds, opening_balance=opening, interest=interest, principal=principal,
                     closing_balance=closing, sponsor_cfads=cf)


def irr(flows: list[float], lo: float = -0.99, hi: float = 1.0, tol: float = 1e-12) -> float | None:
    """Bisection IRR; None if NPV does not change sign on [lo, hi]."""
    def npv(r):
        return sum(f / (1 + r) ** t for t, f in enumerate(flows))
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(300):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


@dataclass(frozen=True)
class Analysis:
    stress: Stress
    cfads: list[float]                # operating years
    dscr: list[float]                 # tenor years
    llcr: list[float]                 # tenor years: PV of remaining tenor CFADS / opening balance
    lockup: list[bool]                # tenor years
    default_level: list[bool]         # tenor years
    shortfall: list[float]            # operating years
    distributions: list[float]        # operating years
    equity_flows: list[float]         # construction years then operating years
    min_dscr: float
    avg_dscr: float
    llcr_cod: float
    min_llcr: float
    plcr_cod: float
    equity_irr: float | None

    @property
    def lockup_years(self) -> int:
        return sum(self.lockup)

    @property
    def default_years(self) -> int:
        return sum(self.default_level)

    @property
    def total_shortfall(self) -> float:
        return sum(self.shortfall)


def analyse(p: ProjectInputs, fin: Financing, s: Stress = NO_STRESS) -> Analysis:
    """Stress operating cash flows against the frozen debt schedule in `fin`.

    Waterfall per operating year: available = cash brought forward + CFADS - debt service. A negative amount is a
    payment shortfall (recorded; no sponsor support, no acceleration). In a tenor year whose DSCR is below the
    lock-up level the cash is trapped; otherwise all of it is distributed. The tail has no debt, so trapped cash
    is always released by the last operating year."""
    cf = operations(p, s).cfads
    n, tenor = p.operation_years, p.debt_tenor
    ds = fin.debt_service + [0.0] * (n - tenor)
    df = discount_factors(p.debt_rate, n)
    dscr = [cf[k] / ds[k] for k in range(tenor)]
    llcr = [sum(cf[j] * df[j] for j in range(k, tenor)) / (df[k - 1] if k else 1.0) / fin.opening_balance[k]
            for k in range(tenor)]
    plcr_cod = sum(c * d for c, d in zip(cf, df)) / fin.opening_balance[0]
    lock = [d < p.lockup_dscr for d in dscr]
    dflt = [d < p.default_dscr for d in dscr]
    cash, shortfall, dist = 0.0, [], []
    for k in range(n):
        avail = cash + cf[k] - ds[k]
        shortfall.append(max(0.0, -avail))
        pay = 0.0 if (k < tenor and lock[k]) else max(0.0, avail)
        cash = max(0.0, avail) - pay
        dist.append(pay)
    equity = [-e for e in fin.equity]
    equity[-1] -= s.capex_overrun * p.capex
    flows = equity + dist
    return Analysis(stress=s, cfads=cf, dscr=dscr, llcr=llcr, lockup=lock, default_level=dflt, shortfall=shortfall,
                    distributions=dist, equity_flows=flows, min_dscr=min(dscr), avg_dscr=sum(dscr) / tenor,
                    llcr_cod=llcr[0], min_llcr=min(llcr), plcr_cod=plcr_cod, equity_irr=irr(flows))
