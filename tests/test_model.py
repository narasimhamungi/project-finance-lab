import math

import pytest

from conftest import tiny
from projectfinancelab.model import ProjectInputs, Stress, analyse, irr, operations, size_debt

PV = 30 / 1.1 + 30 / 1.21                      # PV of tenor CFADS at 10%


def test_hand_calculation_dscr_binding():
    f = size_debt(tiny())
    assert f.binding == "DSCR"
    assert f.debt == pytest.approx(PV / 1.25, abs=1e-9)
    assert f.debt_service == pytest.approx([24.0, 24.0], abs=1e-9)
    assert f.interest[0] == pytest.approx(0.1 * f.debt, abs=1e-12)
    assert f.closing_balance[-1] == pytest.approx(0.0, abs=1e-9)
    a = analyse(tiny(), f)
    assert a.dscr == pytest.approx([1.25, 1.25])
    assert a.plcr_cod == pytest.approx((PV + 30 / 1.331) / f.debt)
    assert a.distributions == pytest.approx([6.0, 6.0, 30.0])
    assert a.equity_flows[0] == pytest.approx(-(100 - f.debt))


def test_hand_calculation_gearing_binding():
    f = size_debt(tiny(max_gearing=0.3))
    assert f.binding == "gearing"
    assert f.debt == pytest.approx(30.0, abs=1e-9)
    assert f.sculpt_dscr == pytest.approx(PV / 30.0)


def test_fee_makes_debt_and_uses_circular():
    f = size_debt(tiny(max_gearing=0.3, upfront_fee=0.02))
    assert f.debt == pytest.approx(30 / (1 - 0.3 * 0.02), abs=1e-9)       # D = 0.3 (100 + 0.02 D)
    assert f.total_uses == pytest.approx(100 + 0.02 * f.debt, abs=1e-9)


def test_idc_is_capitalised_on_the_opening_balance():
    f = size_debt(tiny(construction_years=2, capex_profile=(0.5, 0.5), max_gearing=0.3))
    assert f.idc == pytest.approx([0.0, 0.1 * 0.3 * 50.0])
    assert f.total_uses == pytest.approx(101.5)
    assert f.debt == pytest.approx(30.45)
    assert sum(f.debt_draw) == pytest.approx(f.debt, abs=1e-9)


def test_shipped_example_sizing(shipped):
    f = size_debt(shipped)
    assert f.binding == "DSCR" and f.sculpt_dscr == pytest.approx(1.35)
    assert f.debt / f.total_uses <= shipped.max_gearing
    assert min(f.principal) > 0


def test_tax_is_unlevered_and_floored():
    ops = operations(tiny(tax_rate=0.5, opex_y1=25.0))       # EBITDA 5, depreciation 33.3: no tax
    assert ops.tax == [0.0, 0.0, 0.0]
    ops = operations(tiny(tax_rate=0.5, depreciation_years=1))
    assert ops.tax == pytest.approx([0.0, 15.0, 15.0])     # year 1: depreciation 100 > EBITDA 30


def test_delay_hits_operating_year_one_only():
    base, late = operations(tiny()), operations(tiny(), Stress(delay_months=6))
    assert late.revenue[0] == pytest.approx(base.revenue[0] / 2)
    assert late.revenue[1:] == base.revenue[1:]


def test_capex_overrun_is_equity_funded_and_leaves_debt_alone():
    p = tiny()
    f = size_debt(p)
    a = analyse(p, f, Stress(capex_overrun=0.1))
    assert a.equity_flows[0] == pytest.approx(-(100 - f.debt) - 10.0)
    assert a.dscr == analyse(p, f).dscr


def test_lockup_traps_cash_until_the_tail():
    p = tiny(lockup_dscr=1.2, target_dscr=1.25)
    f = size_debt(p)
    a = analyse(p, f, Stress(revenue_haircut=0.1))           # CFADS 27, DS 24: DSCR 1.125 < 1.2
    assert a.lockup == [True, True]
    assert a.distributions == pytest.approx([0.0, 0.0, 3.0 + 3.0 + 27.0])


def test_shortfall_is_recorded_not_funded():
    p = tiny()
    f = size_debt(p)
    a = analyse(p, f, Stress(revenue_haircut=0.5))           # CFADS 15 vs DS 24
    assert a.shortfall[:2] == pytest.approx([9.0, 9.0])
    assert a.default_level == [True, True]


def test_irr():
    assert irr([-100, 110]) == pytest.approx(0.10, abs=1e-10)
    assert irr([-100, 0, 121]) == pytest.approx(0.10, abs=1e-10)
    assert irr([100, 100]) is None


@pytest.mark.parametrize("change", [dict(debt_tenor=3), dict(capex_profile=(0.5, 0.5)), dict(construction_years=4),
                                    dict(lockup_dscr=1.3), dict(default_dscr=0.9), dict(max_gearing=1.0)])
def test_invalid_inputs_are_rejected(change):
    with pytest.raises(ValueError):
        tiny(**change)


def test_negative_sponsor_cfads_is_rejected():
    with pytest.raises(ValueError):
        size_debt(tiny(opex_y1=40.0))


def test_from_dict_round_trip(cfg):
    p = ProjectInputs.from_dict(cfg["project"])
    assert isinstance(p.capex_profile, tuple) and math.isclose(sum(p.capex_profile), 1.0)
