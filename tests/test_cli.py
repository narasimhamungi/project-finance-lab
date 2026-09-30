from conftest import ROOT
from projectfinancelab.cli import main


def test_run_writes_outputs(tmp_path):
    assert main(["run", "--config", str(ROOT / "examples" / "project_hypothetical.json"), "--out", str(tmp_path)]) == 0
    for name in ("summary.md", "cases.csv", "breakevens.csv", "grid.csv", "sizing_sensitivity.csv", "debt_schedule.csv"):
        assert (tmp_path / name).exists()
    text = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "not any rating agency" in text and "binding constraint: DSCR" in text


def test_verify_log_exit_code(tmp_path):
    assert main(["verify-log", "--log", str(ROOT / "excel" / "regression" / "libreoffice_log.csv")]) == 0
