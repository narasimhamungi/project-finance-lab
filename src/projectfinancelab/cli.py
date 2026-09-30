"""project-finance-lab run --config FILE.json --out DIR
   project-finance-lab regression-cases | verify-log --log FILE.csv

Inputs are the user's; the example file is hypothetical, not market terms and not any agency's criteria.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from . import regression as reg
from .model import ProjectInputs, Stress, analyse, size_debt
from .scenarios import breakevens, grid, run_cases, sizing_sensitivity

DISCLAIMER = ("*Hypothetical inputs for illustration. Not a real project, not market terms, not advice, and not any "
              "rating agency's model, criteria or rating case.*")


def _csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _x(v) -> str:
    return "n/a" if v is None else f"{v:.2f}x"


def _pct(v) -> str:
    return "n/a" if v is None else f"{v:.1%}"


def run(cfg: dict, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    p = ProjectInputs.from_dict(cfg["project"])
    fin = size_debt(p)
    cases = {k: Stress(**v) for k, v in cfg["cases"].items()}
    case_rows = run_cases(p, fin, cases)
    be_rows = breakevens(p, fin)
    grid_rows = grid(p, fin, cfg["grid"]["revenue_haircut"], cfg["grid"]["opex_increase"])
    size_rows = sizing_sensitivity(p, cfg["rate_shifts"])
    sponsor = analyse(p, fin)
    schedule = [{"operating_year": k + 1, "cfads": fin.sponsor_cfads[k], "debt_service": fin.debt_service[k],
                 "interest": fin.interest[k], "principal": fin.principal[k], "opening_balance": fin.opening_balance[k],
                 "closing_balance": fin.closing_balance[k], "dscr": sponsor.dscr[k], "llcr": sponsor.llcr[k]}
                for k in range(p.debt_tenor)]
    for name, rows in (("cases", case_rows), ("breakevens", be_rows), ("grid", grid_rows),
                       ("sizing_sensitivity", size_rows), ("debt_schedule", schedule)):
        _csv(out / f"{name}.csv", rows)

    lines = [f"# {cfg['label']}", "", DISCLAIMER, "", f"Units: {cfg['units']}.", "", "## Sizing (sponsor case)", "",
             f"- Uses {fin.total_uses:,.2f} (capex {sum(fin.capex):,.2f}, IDC {sum(fin.idc):,.2f}, "
             f"fee {sum(fin.fee):,.2f}); debt {fin.debt:,.2f} ({fin.debt / fin.total_uses:.1%} gearing); "
             f"equity {sum(fin.equity):,.2f}",
             f"- Debt capacity at {p.target_dscr:.2f}x target DSCR {fin.debt_dscr_capacity:,.2f}; gearing cap "
             f"{fin.debt_gearing_cap:,.2f}; binding constraint: {fin.binding}; sculpting DSCR {_x(fin.sculpt_dscr)}",
             f"- Debt and uses solved as a fixed point in {fin.iterations} iterations; repayment schedule then frozen",
             "", "## Cases on the frozen debt", "",
             "| Case | Min DSCR | Avg DSCR | LLCR at COD | PLCR at COD | Lock-up yrs | Default-level yrs | "
             "Shortfall | Equity IRR |", "|---|---|---|---|---|---|---|---|---|"]
    for r in case_rows:
        lines.append(f"| {r['case']} | {_x(r['min_dscr'])} | {_x(r['avg_dscr'])} | {_x(r['llcr_cod'])} | "
                     f"{_x(r['plcr_cod'])} | {r['lockup_years']} | {r['default_level_years']} | "
                     f"{r['total_shortfall']:,.2f} | {_pct(r['equity_irr'])} |")
    lines += ["", "## Breakevens on the frozen debt (one lever at a time)", "",
              "| Lever | Threshold | Largest stress before the minimum DSCR falls below it |", "|---|---|---|"]
    for r in be_rows:
        lines.append(f"| {r['lever']} | {r['threshold']} ({r['dscr_level']:.2f}x) | {r['breakeven']:.2%} |")
    lines += ["", "## Interest-rate sizing sensitivity (debt re-sized)", "",
              "| Debt rate | Debt | Gearing | Binding | Sculpting DSCR | Sponsor equity IRR |", "|---|---|---|---|---|---|"]
    for r in size_rows:
        lines.append(f"| {r['debt_rate']:.2%} | {r['debt']:,.2f} | {r['gearing']:.1%} | {r['binding']} | "
                     f"{_x(r['sculpt_dscr'])} | {_pct(r['sponsor_equity_irr'])} |")
    lines += ["", "Full tables: cases.csv, breakevens.csv, grid.csv (minimum DSCR by revenue haircut and opex "
                  "increase), sizing_sensitivity.csv, debt_schedule.csv.", ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return {"financing": fin, "cases": case_rows, "breakevens": be_rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="project-finance-lab")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("run", help="size the debt, run cases, breakevens, grid and sensitivities")
    s.add_argument("--config", required=True)
    s.add_argument("--out", default="outputs")
    s = sub.add_parser("regression-cases", help="write workbook regression cases with Python-expected outputs")
    s.add_argument("--config", default="examples/project_hypothetical.json")
    s.add_argument("--out", default="excel/regression/cases.csv")
    s.add_argument("--random", type=int, default=30)
    s.add_argument("--seed", type=int, default=reg.SEED)
    s = sub.add_parser("verify-log", help="check a spreadsheet run's log against the regression cases")
    s.add_argument("--cases", default="excel/regression/cases.csv")
    s.add_argument("--log", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "run":
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        run(cfg, Path(args.out))
        print(f"wrote {args.out}/summary.md and CSVs")
        return 0
    if args.cmd == "regression-cases":
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        cases = reg.all_cases(cfg, args.random, args.seed)
        reg.write_cases(Path(args.out), cases)
        print(f"{len(cases)} regression cases written to {args.out}")
        return 0
    result = reg.verify_log(Path(args.cases), Path(args.log))
    print(reg.report_text(result, args.log), end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
