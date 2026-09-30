"""Regression cases for the workbook, and a verifier for spreadsheet runs.

The workbook (excel/project_finance_model.xlsx) reproduces model.py in formulas. Each case sets the sponsor inputs,
a stress, and the converged debt and uses that the Python fixed point produced (the workbook takes these as pasted
values and checks that its own formulas return the same numbers; see docs/model_spec.md, "Circularity"). A
spreadsheet run - the LibreOffice runner, or the VBA harness in Excel - logs every output; verify_log() checks
the log against the Python-expected values independently of any comparison the runner made itself.

Random inputs are generated to exercise the formulas. They are not observed projects or market terms.

This module is also the single source of the workbook's cell map: excel/build_workbook.py imports it.
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

from .model import ProjectInputs, Stress, analyse, size_debt

SEED = 20260930
TOL = 1e-6
PASS_TEXT = "ALL CHECKS PASS"
NA = "n/a"

INPUT_CELLS = {  # field -> cell on the Inputs sheet
    "construction_years": "C5", "capex": "C6", "capex_y1": "C7", "capex_y2": "C8", "capex_y3": "C9",
    "operation_years": "C10", "revenue_y1": "C11", "revenue_growth": "C12", "opex_y1": "C13", "opex_growth": "C14",
    "tax_rate": "C15", "depreciation_years": "C16", "debt_rate": "C17", "debt_tenor": "C18", "target_dscr": "C19",
    "max_gearing": "C20", "upfront_fee": "C21", "lockup_dscr": "C22", "default_dscr": "C23",
    "revenue_haircut": "C26", "opex_increase": "C27", "delay_months": "C28", "capex_overrun": "C29",
    "debt_pasted": "C32", "uses_pasted": "C33",
}
OUTPUTS = [  # (field, cell, kind); kind: num, text, irr (number or n/a)
    ("debt_calc", "Operations!C33", "num"), ("uses_calc", "Construction!C15", "num"),
    ("sculpt_dscr", "Operations!C34", "num"), ("binding", "Operations!C35", "text"),
    ("min_dscr", "Analysis!C28", "num"), ("avg_dscr", "Analysis!C29", "num"), ("llcr_cod", "Analysis!C30", "num"),
    ("min_llcr", "Analysis!C31", "num"), ("plcr_cod", "Analysis!C32", "num"),
    ("lockup_years", "Analysis!C33", "num"), ("default_years", "Analysis!C34", "num"),
    ("total_shortfall", "Analysis!C35", "num"), ("total_distributions", "Analysis!C36", "num"),
    ("equity_irr", "Analysis!C37", "irr"), ("checks_overall", "Checks!B17", "text"),
]
FIELDS = [f for f, _, _ in OUTPUTS]
KIND = {f: k for f, _, k in OUTPUTS}
INPUT_COLUMNS = ["case_id", "description"] + list(INPUT_CELLS)
LOG_COLUMNS = ["case_id", "field", "actual", "runner_pass"]
PROJECT_FIELDS = [f for f in INPUT_CELLS if f not in ("capex_y1", "capex_y2", "capex_y3", "revenue_haircut",
                                                     "opex_increase", "delay_months", "capex_overrun",
                                                     "debt_pasted", "uses_pasted")]


def _row(case_id: str, description: str, project: dict, stress: dict) -> dict:
    p = ProjectInputs.from_dict(project)
    s = Stress(**stress)
    fin = size_debt(p)
    row = {"case_id": case_id, "description": description}
    row.update({k: project[k] for k in PROJECT_FIELDS})
    prof = list(project["capex_profile"]) + [0.0] * (3 - len(project["capex_profile"]))
    row.update({"capex_y1": prof[0], "capex_y2": prof[1], "capex_y3": prof[2]})
    row.update({"revenue_haircut": s.revenue_haircut, "opex_increase": s.opex_increase,
                "delay_months": s.delay_months, "capex_overrun": s.capex_overrun,
                "debt_pasted": fin.debt, "uses_pasted": fin.total_uses})
    return row


def project_from_row(row: dict) -> tuple[ProjectInputs, Stress]:
    num = {k: float(row[k]) for k in INPUT_COLUMNS[2:]}
    nc = int(num["construction_years"])
    d = {k: num[k] for k in PROJECT_FIELDS}
    for k in ("construction_years", "operation_years", "depreciation_years", "debt_tenor"):
        d[k] = int(d[k])
    d["capex_profile"] = tuple(num[f"capex_y{i}"] for i in range(1, nc + 1))
    s = Stress(num["revenue_haircut"], num["opex_increase"], num["delay_months"], num["capex_overrun"])
    return ProjectInputs.from_dict(d), s


def shipped_cases(cfg: dict) -> list[dict]:
    return [_row(f"S{i:02d}", f"shipped config case {name}", cfg["project"], stress)
            for i, (name, stress) in enumerate(cfg["cases"].items(), 1)]


def random_cases(n: int, seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for i in range(1, n + 1):
        nc = rng.randint(1, 3)
        raw = [rng.randint(1, 9) for _ in range(nc)]
        prof = [round(x / sum(raw), 4) for x in raw[:-1]]
        prof.append(round(1 - sum(prof), 4))
        no = rng.randint(15, 30)
        capex = round(rng.uniform(100, 800), 2)
        rev = round(capex * rng.uniform(0.12, 0.20), 2)
        target = round(rng.uniform(1.20, 1.60), 4)
        lock = round(rng.uniform(1.05, target), 4)
        project = {"construction_years": nc, "capex": capex, "capex_profile": prof, "operation_years": no,
                   "revenue_y1": rev, "revenue_growth": round(rng.uniform(0.0, 0.03), 4),
                   "opex_y1": round(rev * rng.uniform(0.15, 0.35), 2), "opex_growth": round(rng.uniform(0.0, 0.035), 4),
                   "tax_rate": round(rng.uniform(0.0, 0.30), 4), "depreciation_years": rng.randint(10, no),
                   "debt_rate": round(rng.uniform(0.03, 0.09), 4), "debt_tenor": rng.randint(8, no - 2),
                   "target_dscr": target, "max_gearing": round(rng.uniform(0.60, 0.90), 4),
                   "upfront_fee": round(rng.uniform(0.0, 0.025), 4), "lockup_dscr": lock,
                   "default_dscr": round(rng.uniform(1.0, lock), 4)}
        stress = {"revenue_haircut": round(rng.uniform(0.0, 0.25), 4), "opex_increase": round(rng.uniform(0.0, 0.40), 4),
                  "delay_months": rng.choice([0, 0, 0, 3, 6]), "capex_overrun": round(rng.uniform(0.0, 0.10), 4)}
        out.append(_row(f"R{i:02d}", f"random seed {seed} draw {i}", project, stress))
    return out


def all_cases(cfg: dict, n_random: int = 30, seed: int = SEED) -> list[dict]:
    return shipped_cases(cfg) + random_cases(n_random, seed)


def expected(row: dict) -> dict:
    p, s = project_from_row(row)
    fin = size_debt(p)
    a = analyse(p, fin, s)
    return {"debt_calc": fin.debt, "uses_calc": fin.total_uses, "sculpt_dscr": fin.sculpt_dscr, "binding": fin.binding,
            "min_dscr": a.min_dscr, "avg_dscr": a.avg_dscr, "llcr_cod": a.llcr_cod, "min_llcr": a.min_llcr,
            "plcr_cod": a.plcr_cod, "lockup_years": float(a.lockup_years), "default_years": float(a.default_years),
            "total_shortfall": a.total_shortfall, "total_distributions": sum(a.distributions),
            "equity_irr": NA if a.equity_irr is None else a.equity_irr, "checks_overall": PASS_TEXT}


def _text(v) -> str:
    return repr(float(v)) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)


def write_cases(path: Path, cases: list[dict]) -> None:
    """One row per case: inputs, then exp_<field>. No field contains a comma or a quote."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(INPUT_COLUMNS + [f"exp_{f}" for f in FIELDS])
        for c in cases:
            e = expected(c)
            w.writerow([_text(c[k]) for k in INPUT_COLUMNS] + [_text(e[f]) for f in FIELDS])


def read_cases(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def matches(field: str, expected_text: str, actual_text: str) -> bool:
    kind = KIND[field]
    if kind == "text" or (kind == "irr" and (expected_text == NA or actual_text == NA)):
        return str(actual_text).strip() == str(expected_text).strip()
    try:
        e, a = float(expected_text), float(actual_text)
    except ValueError:
        return False
    return math.isfinite(a) and abs(a - e) <= TOL


def verify_log(cases_path: Path, log_path: Path) -> dict:
    """Every case x field must appear exactly once; missing, duplicated or unexpected rows fail."""
    cases = read_cases(cases_path)
    exp = {(r["case_id"], f): r[f"exp_{f}"] for r in cases for f in FIELDS}
    seen, duplicates, unexpected = {}, [], []
    with open(log_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            key = (row["case_id"].strip(), row["field"].strip())
            if key not in exp:
                unexpected.append(key)
            elif key in seen:
                duplicates.append(key)
            else:
                seen[key] = row
    missing = [k for k in exp if k not in seen]
    failures, disagreements = [], []
    for key, row in seen.items():
        ok = matches(key[1], exp[key], row["actual"])
        if not ok:
            failures.append({"case_id": key[0], "field": key[1], "expected": exp[key], "actual": row["actual"]})
        flag = str(row.get("runner_pass", "")).strip().upper()
        if flag in ("TRUE", "FALSE") and (flag == "TRUE") != ok:
            disagreements.append(key)
    passed = not (missing or duplicates or unexpected or failures or disagreements)
    return {"passed": passed, "cases": len(cases), "checks": len(exp), "logged": len(seen), "missing": missing,
            "duplicates": duplicates, "unexpected": unexpected, "failures": failures,
            "runner_disagreements": disagreements}


def report_text(r: dict, log_name: str) -> str:
    lines = [f"Verification of {log_name}: {'PASS' if r['passed'] else 'FAIL'}",
             f"- {r['cases']} cases x {len(FIELDS)} fields = {r['checks']} checks; {r['logged']} logged",
             f"- missing {len(r['missing'])}, duplicated {len(r['duplicates'])}, unexpected {len(r['unexpected'])}",
             f"- value mismatches {len(r['failures'])} (tolerance {TOL:g} absolute)",
             f"- rows where the runner's own pass flag disagrees with this check: {len(r['runner_disagreements'])}"]
    lines += [f"  - {f['case_id']} {f['field']}: expected {f['expected']}, got {f['actual']}" for f in r["failures"][:20]]
    return "\n".join(lines) + "\n"
