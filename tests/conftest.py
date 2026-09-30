import json
from pathlib import Path

import pytest

from projectfinancelab.model import ProjectInputs

ROOT = Path(__file__).resolve().parents[1]


def tiny(**kw) -> ProjectInputs:
    """Hand-checkable project: 1 construction year, CFADS 30 a year for 3 years, 2-year tenor at 10%."""
    base = dict(construction_years=1, capex=100.0, capex_profile=(1.0,), operation_years=3, revenue_y1=30.0,
                revenue_growth=0.0, opex_y1=0.0, opex_growth=0.0, tax_rate=0.0, depreciation_years=3, debt_rate=0.10,
                debt_tenor=2, target_dscr=1.25, max_gearing=0.9, upfront_fee=0.0, lockup_dscr=1.1, default_dscr=1.0)
    base.update(kw)
    return ProjectInputs(**base)


@pytest.fixture
def cfg():
    return json.loads((ROOT / "examples" / "project_hypothetical.json").read_text(encoding="utf-8"))


@pytest.fixture
def shipped(cfg):
    return ProjectInputs.from_dict(cfg["project"])
