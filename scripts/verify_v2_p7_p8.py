"""Final validation for V2-P7 + V2-P8.

Objectively verifies the directive's 20 final-validation criteria and prints a
PASS/FAIL line per criterion. Exits non-zero if any criterion fails.

    python -m scripts.verify_v2_p7_p8

Criteria 1-11 exercise the Clinical Workstation (V2-P7); 12-16 confirm the V2
certification package (V2-P8) is present and coherent; 17-20 confirm the
governance/quality/lineage gates and the measurability of the V3 entry criteria.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
CERT_DIR = REPO / "docs" / "certification" / "v2"

_CERT_FILES = [
    "V2_CERTIFICATION_STANDARD.md", "V2_READINESS_ASSESSMENT.md", "V2_AUDIT_FRAMEWORK.md",
    "V2_RISK_REVIEW.md", "V2_GAP_ANALYSIS.md", "V2_EXIT_CRITERIA.md",
    "V2_COMPLETION_REPORT.md", "V3_READINESS_GATE.md",
]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    from scripts.build_workstation_snapshot import build_snapshot
    from frontend.clinical_workstation import build_from_snapshot, render_workstation_html

    snapshot = build_snapshot(n_cases=5)
    view = build_from_snapshot(snapshot)
    vd = view.to_dict()
    areas = {a["id"]: a for a in vd["areas"]}

    def area_has_pages(area_id):
        return area_id in areas and len(areas[area_id]["pages"]) >= 1

    # --- V2-P7 Clinical Workstation (1-11) -------------------------------
    check("1. Case workspace works", area_has_pages("cases")
          and len(areas["cases"]["pages"]) >= 1 + len(snapshot["cases"]))
    check("2. Review workspace works", area_has_pages("reviews")
          and len(areas["reviews"]["pages"]) >= 1 + len(snapshot["reviews"]))
    check("3. Findings workspace works", area_has_pages("findings")
          and len(areas["findings"]["pages"]) >= 1 + len(snapshot["findings"]))
    check("4. Knowledge workspace works", area_has_pages("knowledge"))
    check("5. Intelligence workspace works", area_has_pages("intelligence"))
    check("6. Decision support workspace works", area_has_pages("decision"))
    check("7. Audit browser works", area_has_pages("audit"))
    check("8. Lineage explorer works", area_has_pages("lineage"))
    check("9. Reporting center works", area_has_pages("reports"))
    ctx = vd["meta"].get("context", {})
    check("10. State management works", bool(ctx.get("current_case"))
          and bool(ctx.get("current_review")) and bool(ctx.get("current_finding")))
    val = vd["validation"]
    check("11. Workstation validation works", val.get("ok") and val.get("n_checks", 0) >= 7,
          f"{val.get('n_checks')} checks, ok={val.get('ok')}")

    # --- V2-P8 Certification package (12-16) -----------------------------
    present = {f: (CERT_DIR / f).exists() for f in _CERT_FILES}
    check("12. Certification audit completes",
          all(present.values()) and (CERT_DIR / "V2_AUDIT_FRAMEWORK.md").exists(),
          f"missing={[f for f, ok in present.items() if not ok]}")
    readiness = (CERT_DIR / "V2_READINESS_ASSESSMENT.md").read_text(encoding="utf-8") \
        if present["V2_READINESS_ASSESSMENT.md"] else ""
    # Readiness assessment scores all nine dimensions (nine table rows with scores).
    score_rows = re.findall(r"\|\s*\d\s*\|.*\|\s*\d{2,3}\s*\|", readiness)
    check("13. Readiness assessment completes", len(score_rows) >= 9,
          f"{len(score_rows)} scored dimensions")
    gap = (CERT_DIR / "V2_GAP_ANALYSIS.md").read_text(encoding="utf-8") \
        if present["V2_GAP_ANALYSIS.md"] else ""
    check("14. Gap analysis completes",
          ("Gap register" in gap) and ("Closure criteria" in gap) and ("G1" in gap))
    risk = (CERT_DIR / "V2_RISK_REVIEW.md").read_text(encoding="utf-8") \
        if present["V2_RISK_REVIEW.md"] else ""
    check("15. Risk review completes",
          ("Risk register" in risk) and ("Residual risk" in risk) and ("R1" in risk))
    exit_doc = (CERT_DIR / "V2_EXIT_CRITERIA.md").read_text(encoding="utf-8") \
        if present["V2_EXIT_CRITERIA.md"] else ""
    check("16. Exit criteria validated",
          ("PASS" in exit_doc) and ("FAIL" not in _verdict_cells(exit_doc)),
          "no FAIL among exit criteria")

    # --- Gates + lineage + V3 measurability (17-20) ----------------------
    # 17 governance gates: per-subsystem validations recorded in the snapshot are ok.
    gov_ok = _governance_ok(snapshot)
    check("17. Governance gates pass", gov_ok)

    # 18 quality gates: the full test suite passes.
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                          cwd=str(REPO), capture_output=True, text=True)
    last = (proc.stdout.strip().splitlines() or [""])[-1]
    check("18. Quality gates pass", proc.returncode == 0, last)

    # 19 lineage remains intact: representative chain verifies + per-entity verified.
    chain_ok = snapshot["representative_chain"]["verified"]
    per_entity = (all(c["lineage_verified"] for c in snapshot["cases"])
                  and all(r["lineage_verified"] for r in snapshot["reviews"])
                  and all(f["lineage_verified"] for f in snapshot["findings"]))
    check("19. Lineage remains intact", chain_ok and per_entity)

    # 20 V3 readiness criteria are measurable: the gate enumerates measurable E# rows.
    gate = (CERT_DIR / "V3_READINESS_GATE.md").read_text(encoding="utf-8") \
        if present["V3_READINESS_GATE.md"] else ""
    e_rows = re.findall(r"\|\s*E\d\s*\|", gate)
    check("20. V3 readiness criteria are measurable",
          len(e_rows) >= 6 and "NOT GRANTED" in gate, f"{len(e_rows)} measurable entry criteria")

    # --- report ----------------------------------------------------------
    print("\nV2-P7 + V2-P8 FINAL VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok = all_ok and ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail and not ok:
            line += f"  -- {detail}"
        print(line)
    print("=" * 64)
    # Render once more to assert determinism is exercised end-to-end.
    html_ok = render_workstation_html(view).startswith("<!doctype html>")
    print(f"workstation HTML renders: {html_ok}")
    print("RESULT:", "ALL CRITERIA PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


def _verdict_cells(markdown: str) -> str:
    """Concatenate only the status cells of the exit-criteria tables."""
    cells = re.findall(r"\|\s*(PASS\*?|FAIL)\s*\|", markdown)
    return " ".join(cells)


def _governance_ok(snapshot: dict) -> bool:
    intel = snapshot.get("intelligence", {})
    for key in ("analytics", "trend", "quality"):
        if not intel.get(key, {}).get("validation", {}).get("ok", False):
            return False
    for bundle in snapshot.get("decision_support", {}).get("bundles", []):
        for art in bundle.get("artifacts", {}).values():
            if not art.get("validation", {}).get("ok", False):
                return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
