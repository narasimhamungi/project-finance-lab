import csv
import json

import pytest

from conftest import ROOT
from projectfinancelab import regression as reg

CASES = ROOT / "excel" / "regression" / "cases.csv"
LOG = ROOT / "excel" / "regression" / "libreoffice_log.csv"


@pytest.fixture(scope="module")
def rows():
    return reg.read_cases(CASES)


def test_committed_cases_match_a_fresh_generation(tmp_path, cfg):
    """Numbers compared to 1e-12 relative, not as text: C libraries on different platforms (e.g. Windows vs
    Linux) may round pow() differently in the last digit, which is not a stale file."""
    fresh = tmp_path / "cases.csv"
    reg.write_cases(fresh, reg.all_cases(cfg))
    new, old = reg.read_cases(fresh), reg.read_cases(CASES)
    assert [r["case_id"] for r in new] == [r["case_id"] for r in old], "cases.csv is stale: run regression-cases"
    for a, b in zip(new, old):
        for k in a:
            try:
                x, y = float(a[k]), float(b[k])
            except ValueError:
                assert a[k] == b[k], (a["case_id"], k)
            else:
                assert x == pytest.approx(y, rel=1e-12, abs=1e-12), (a["case_id"], k)


def test_cases_cover_every_regime(rows):
    assert {r["exp_binding"] for r in rows} == {"DSCR", "gearing"}
    assert {r["construction_years"] for r in rows} == {"1.0", "2.0", "3.0"}
    assert any(float(r["exp_lockup_years"]) > 0 for r in rows)
    assert any(float(r["exp_default_years"]) > 0 for r in rows)
    assert any(float(r["exp_total_shortfall"]) > 0 for r in rows)
    assert any(r["exp_equity_irr"] != reg.NA and float(r["exp_equity_irr"]) < 0 for r in rows)


def test_no_field_needs_csv_quoting():
    assert '"' not in CASES.read_text(encoding="utf-8")


def test_committed_libreoffice_log_verifies():
    assert reg.verify_log(CASES, LOG)["passed"]


def _write_log(path, rows, mutate=None):
    out = [{"case_id": r["case_id"], "field": f, "actual": r[f"exp_{f}"], "runner_pass": "TRUE"}
           for r in rows for f in reg.FIELDS]
    if mutate:
        out = mutate(out)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=reg.LOG_COLUMNS)
        w.writeheader()
        w.writerows(out)


def test_verifier_catches_every_failure_mode(tmp_path, rows):
    log = tmp_path / "log.csv"
    _write_log(log, rows)
    assert reg.verify_log(CASES, log)["passed"]
    for mutate, key in [(lambda o: o[1:], "missing"), (lambda o: o + o[:1], "duplicates"),
                        (lambda o: o + [{**o[0], "case_id": "ZZ"}], "unexpected"),
                        (lambda o: [{**o[0], "actual": "999"}] + o[1:], "failures")]:
        _write_log(log, rows, mutate)
        r = reg.verify_log(CASES, log)
        assert not r["passed"] and r[key]


def test_matching_rules():
    assert reg.matches("min_dscr", "1.2", "1.2000004")
    assert not reg.matches("min_dscr", "1.2", "1.20001")
    assert reg.matches("equity_irr", "n/a", "n/a") and not reg.matches("equity_irr", "0.1", "n/a")
    assert not reg.matches("binding", "DSCR", "gearing")


def test_rows_round_trip_to_inputs(rows):
    for r in rows:
        p, s = reg.project_from_row(r)
        assert p.construction_years == int(float(r["construction_years"]))
