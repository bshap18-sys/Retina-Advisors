"""Eval runner for the Retina Advisors dispute analyzer.

Runs all 26 scenarios from eval/scenarios.py against the live tool and
prints a scored summary table. Scenarios 1-25 call analyze_dispute() and
grade_report(). Scenario 26 calls evaluate_report() directly against a
deliberately flawed synthesis output to test the evaluator-optimizer loop.

Usage (from project root):
    .venv\\Scripts\\python.exe -m eval.eval_runner
    .venv\\Scripts\\python.exe -m eval.eval_runner --must-pass-only

Must-pass scenarios (zero tolerance): 1, 2, 8, 12, 13, 16, 20, 26
Acceptable variance scenarios: 4, 15, 21, 24
Target: 23/26 overall, 8/8 must-pass
"""

import argparse
import asyncio
import datetime
import sys
from pathlib import Path

# src/ is not on sys.path when running as a module from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from retina.analyzer import analyze_dispute, evaluate_report  # noqa: E402
from eval.grader import grade_report, grade_scenario_26  # noqa: E402
from eval.scenarios import (  # noqa: E402
    ALL_SCENARIOS,
    MUST_PASS_IDS,
    ACCEPTABLE_VARIANCE_IDS,
    SCENARIO_26_FLAWED_OUTPUT,
)

SEP = "=" * 82
HDR = (
    f"   {'#':>2}  {'':1}  {'VAR':3}  {'RESULT':6}  {'L1':4}  {'L2':>2}"
    f"  {'Classification':<26}  {'Rec':<9}  Signals"
)
DIV = (
    f"   {'--':>2}  {'-':1}  {'---':3}  {'------':6}  {'----':4}  {'--':>2}"
    f"  {'-'*26}  {'-'*9}  -------"
)


def _trunc(s: str, width: int) -> str:
    if len(s) > width:
        return s[: width - 1] + "."
    return s.ljust(width)


async def _run_standard(scenario_input: dict, expected: dict) -> tuple[dict, dict]:
    result = await analyze_dispute(scenario_input)
    grade = await grade_report(result["report_xml"], expected, scenario_input)
    return result, grade


async def _run_evaluator(scenario_input: dict) -> dict:
    return await evaluate_report(SCENARIO_26_FLAWED_OUTPUT, scenario_input)


async def run_all(must_pass_only: bool = False) -> None:
    today = datetime.date.today().isoformat()
    mode_label = "  (must-pass only)" if must_pass_only else ""
    print(SEP)
    print(f"RETINA ADVISORS EVAL RUN  --  {today}{mode_label}")
    print(SEP)
    print(HDR)
    print(DIV)

    scenarios = (
        [(n, s, e) for n, s, e in ALL_SCENARIOS if n in MUST_PASS_IDS]
        if must_pass_only
        else ALL_SCENARIOS
    )

    rows: list[dict] = []

    for idx, (num, scenario_input, expected) in enumerate(scenarios):
        is_must_pass = num in MUST_PASS_IDS
        is_acceptable_variance = num in ACCEPTABLE_VARIANCE_IDS
        is_evaluator_mode = "overall_result" in expected

        if is_evaluator_mode:
            evaluator_output = await _run_evaluator(scenario_input)
            grade = grade_scenario_26(evaluator_output)
            passed = grade["passed"]

            fc = grade["failed_criteria"]
            n_found = len(fc["found"])
            n_required = len(fc["required"])

            l1_str = "--  "
            l2_str = "--"
            cls_str = _trunc("[evaluator mode]", 26)
            rec_str = _trunc("--", 9)
            sig_str = f"{n_found}/{n_required}"

            extra_lines: list[str] = []
            if not passed:
                or_check = grade["overall_result"]
                if not or_check["passed"]:
                    extra_lines.append(
                        f"    ^ evaluator result: got '{or_check['actual']}'"
                        f", expected 'revision_required'"
                    )
                if fc["missing"]:
                    extra_lines.append(f"    ^ missing criteria: {', '.join(fc['missing'])}")
        else:
            result, grade = await _run_standard(scenario_input, expected)
            passed = grade["passed"]
            layer1 = grade["layer1"]
            layer2 = grade["layer2"]

            l1_str = "OK  " if layer1["passed"] else "FAIL"
            l2_str = str(layer2["quality_score"])
            cls_actual = layer1["classification"]["actual"] or ""
            cls_str = _trunc(cls_actual, 26)
            rec_actual = layer1["recommendation"]["actual"] or "--"
            rec_str = _trunc(rec_actual, 9)

            ks = layer1["key_signals"]
            n_ks_found = len(ks["found"])
            n_ks_total = n_ks_found + len(ks["missing"])
            sig_str = f"{n_ks_found}/{n_ks_total}"

            extra_lines = []
            if not layer1["passed"]:
                cls_check = layer1["classification"]
                if not cls_check["passed"]:
                    extra_lines.append(
                        f"    ^ classification: got '{cls_check['actual']}'"
                        f", expected '{cls_check['expected']}'"
                    )
                rec_check = layer1["recommendation"]
                if not rec_check["passed"]:
                    extra_lines.append(
                        f"    ^ recommendation: got '{rec_check['actual']}'"
                        f", expected '{rec_check['expected']}'"
                    )
                conf_check = layer1["confidence"]
                if not conf_check["passed"]:
                    extra_lines.append(
                        f"    ^ confidence: got '{conf_check['actual']}'"
                        f", expected '{conf_check['expected']}'"
                    )
                if ks["missing"]:
                    extra_lines.append(f"    ^ missing signals: {', '.join(ks['missing'])}")
                fp = layer1.get("first_paragraph")
                if fp and not fp["passed"]:
                    extra_lines.append(f"    ^ first_para missing: {', '.join(fp['missing'])}")
                el = layer1.get("evidence_lead")
                if el and not el["passed"]:
                    extra_lines.append(f"    ^ evidence_lead missing: {', '.join(el['missing'])}")
            elif not layer2["quality_pass"]:
                extra_lines.append(f"    ^ quality: {layer2['quality_notes']}")

        pfx = "!!" if (is_must_pass and not passed) else "  "
        mp_flag = "*" if is_must_pass else " "
        if is_evaluator_mode:
            var_flag = "EVL"
        elif is_acceptable_variance:
            var_flag = "~  "
        else:
            var_flag = "   "
        result_str = "PASS" if passed else "FAIL"

        row_line = (
            f"{pfx} {num:>2}  {mp_flag}  {var_flag}  {result_str:<6}  "
            f"{l1_str}  {l2_str:>2}  {cls_str}  {rec_str}  {sig_str}"
        )
        print(row_line)
        for line in extra_lines:
            print(line)

        rows.append({"num": num, "is_must_pass": is_must_pass, "passed": passed})

        if idx < len(scenarios) - 1:
            await asyncio.sleep(2)

    total = len(rows)
    passed_count = sum(1 for r in rows if r["passed"])
    mp_rows = [r for r in rows if r["is_must_pass"]]
    mp_passed = sum(1 for r in mp_rows if r["passed"])
    mp_total = len(mp_rows)
    mp_failures = sorted(r["num"] for r in mp_rows if not r["passed"])
    pct = round(passed_count / total * 100)

    print(SEP)
    print("SUMMARY")
    print(f"Overall:     {passed_count}/{total} passed  ({pct}%)")
    if mp_failures:
        failure_ids = ", ".join(f"{n:02d}" for n in mp_failures)
        print(f"Must-pass:   {mp_passed}/{mp_total} passed  -- MUST-PASS FAILURES: [{failure_ids}]")
        print("Verdict:     LAUNCH: BLOCKED")
    else:
        print(f"Must-pass:   {mp_passed}/{mp_total} passed")
        print("Verdict:     LAUNCH: GO")
    print(SEP)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retina Advisors eval runner")
    parser.add_argument(
        "--must-pass-only",
        action="store_true",
        help="Run only the 8 must-pass scenarios (1, 2, 8, 12, 13, 16, 20, 26)",
    )
    args = parser.parse_args()
    asyncio.run(run_all(must_pass_only=args.must_pass_only))
