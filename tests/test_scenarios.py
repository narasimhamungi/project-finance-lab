import pytest

from conftest import tiny
from projectfinancelab.model import Stress, analyse, size_debt
from projectfinancelab.scenarios import breakeven, breakevens, grid, run_cases, sizing_sensitivity


def test_revenue_breakeven_hand_calculation():
    p = tiny()
    f = size_debt(p)                    # CFADS 30, DS 24: DSCR 1.0 when revenue falls 20%
    assert breakeven(p, f, "revenue_haircut", 1.0) == pytest.approx(0.2, abs=1e-9)
    assert breakeven(p, f, "revenue_haircut", 1.1) == pytest.approx(1 - 26.4 / 30, abs=1e-9)


def test_breakeven_sits_on_the_threshold(shipped):
    f = size_debt(shipped)
    for lever in ("revenue_haircut", "opex_increase"):
        x = breakeven(shipped, f, lever, 1.0)
        assert analyse(shipped, f, Stress(**{lever: x})).min_dscr == pytest.approx(1.0, abs=1e-9)
        assert analyse(shipped, f, Stress(**{lever: x + 1e-6})).min_dscr < 1.0


def test_breakevens_are_ordered_by_threshold(shipped):
    f = size_debt(shipped)
    rows = {(r["lever"], r["dscr_level"]): r["breakeven"] for r in breakevens(shipped, f)}
    for lever in ("revenue_haircut", "opex_increase"):
        assert rows[(lever, 1.0)] > rows[(lever, shipped.default_dscr)] > rows[(lever, shipped.lockup_dscr)]


def test_breakeven_is_zero_when_already_below():
    p = tiny()
    f = size_debt(p)
    assert breakeven(p, f, "revenue_haircut", 1.3) == 0.0


def test_grid_is_monotone(shipped):
    f = size_debt(shipped)
    g = {(r["revenue_haircut"], r["opex_increase"]): r["min_dscr"]
         for r in grid(shipped, f, [0, 0.1, 0.2], [0, 0.2, 0.4])}
    assert g[(0, 0)] == pytest.approx(shipped.target_dscr)
    assert g[(0.1, 0)] < g[(0, 0)] and g[(0, 0.2)] < g[(0, 0)] and g[(0.2, 0.4)] == min(g.values())


def test_sponsor_case_reproduces_sizing(shipped, cfg):
    f = size_debt(shipped)
    rows = run_cases(shipped, f, {k: Stress(**v) for k, v in cfg["cases"].items()})
    sponsor = next(r for r in rows if r["case"] == "sponsor")
    assert sponsor["min_dscr"] == pytest.approx(f.sculpt_dscr) and sponsor["llcr_cod"] == pytest.approx(f.sculpt_dscr)


def test_sizing_sensitivity_re_sizes_and_can_switch_constraint(shipped):
    rows = sizing_sensitivity(shipped, [-0.01, 0.0, 0.01])
    assert rows[0]["debt"] > rows[2]["debt"]
    assert {r["binding"] for r in rows} == {"DSCR", "gearing"}
