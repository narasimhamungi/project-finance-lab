"""Property tests: identities that must hold for any valid project, not just the shipped one."""
import pytest
from hypothesis import given, settings, strategies as st

from projectfinancelab.model import ProjectInputs, Stress, analyse, size_debt


@st.composite
def projects(draw):
    nc = draw(st.integers(1, 3))
    raw = draw(st.lists(st.integers(1, 9), min_size=nc, max_size=nc))
    no = draw(st.integers(10, 30))
    capex = draw(st.floats(50, 1000))
    rev = capex * draw(st.floats(0.10, 0.22))
    target = draw(st.floats(1.15, 1.8))
    lock = draw(st.floats(1.0, target))
    return ProjectInputs(
        construction_years=nc, capex=capex, capex_profile=tuple(x / sum(raw) for x in raw), operation_years=no,
        revenue_y1=rev, revenue_growth=draw(st.floats(0, 0.03)), opex_y1=rev * draw(st.floats(0.1, 0.4)),
        opex_growth=draw(st.floats(0, 0.03)), tax_rate=draw(st.floats(0, 0.35)),
        depreciation_years=draw(st.integers(5, no)), debt_rate=draw(st.floats(0.02, 0.10)),
        debt_tenor=draw(st.integers(3, no - 1)), target_dscr=target, max_gearing=draw(st.floats(0.5, 0.95)),
        upfront_fee=draw(st.floats(0, 0.03)), lockup_dscr=lock, default_dscr=draw(st.floats(1.0, lock)))


@settings(max_examples=150, deadline=None)
@given(projects())
def test_sizing_identities(p):
    f = size_debt(p)
    assert f.debt == pytest.approx(min(f.debt_dscr_capacity, p.max_gearing * f.total_uses), rel=1e-10)
    assert sum(f.debt_draw) == pytest.approx(f.debt, rel=1e-10)                        # balance at COD
    assert sum(f.principal) == pytest.approx(f.debt, rel=1e-9)
    assert abs(f.closing_balance[-1]) <= 1e-8 * f.debt
    assert sum(f.debt_draw) + sum(f.equity) == pytest.approx(f.total_uses, rel=1e-12)  # sources = uses
    assert f.sculpt_dscr >= p.target_dscr - 1e-12


@settings(max_examples=150, deadline=None)
@given(projects())
def test_llcr_and_dscr_equal_the_sculpting_dscr_on_the_sizing_case(p):
    f = size_debt(p)
    a = analyse(p, f)
    assert a.dscr == pytest.approx([f.sculpt_dscr] * p.debt_tenor, rel=1e-9)
    assert a.llcr == pytest.approx([f.sculpt_dscr] * p.debt_tenor, rel=1e-9)


@settings(max_examples=100, deadline=None)
@given(projects(), st.floats(0, 0.6), st.floats(0, 0.6), st.floats(0, 1))
def test_min_dscr_never_rises_with_more_stress(p, h, extra, o):
    f = size_debt(p)
    assert analyse(p, f, Stress(revenue_haircut=h + extra * (1 - h))).min_dscr <= \
        analyse(p, f, Stress(revenue_haircut=h)).min_dscr + 1e-12
    assert analyse(p, f, Stress(opex_increase=o + extra)).min_dscr <= analyse(p, f, Stress(opex_increase=o)).min_dscr + 1e-12


@settings(max_examples=100, deadline=None)
@given(projects(), st.floats(0, 0.5), st.floats(0, 0.5), st.sampled_from([0, 3, 6, 12]))
def test_stress_never_touches_the_debt_and_cash_is_conserved(p, h, o, m):
    f = size_debt(p)
    ds_before = list(f.debt_service)
    a = analyse(p, f, Stress(revenue_haircut=h, opex_increase=o, delay_months=m))
    assert f.debt_service == ds_before
    assert [d * s for d, s in zip(a.dscr, f.debt_service)] == pytest.approx(a.cfads[:p.debt_tenor], rel=1e-9)
    ds = f.debt_service + [0.0] * (p.operation_years - p.debt_tenor)
    # distributions = sum(CFADS - debt service) + unpaid shortfalls, because the tail releases all trapped cash
    assert sum(a.distributions) == pytest.approx(sum(c - d for c, d in zip(a.cfads, ds)) + a.total_shortfall,
                                                 rel=1e-9, abs=1e-9)
