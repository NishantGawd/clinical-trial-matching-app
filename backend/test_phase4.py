import asyncio
import json
import os
import time
from pathlib import Path
from typing import cast, List, Dict, Any

from agents.graph import build_clinical_matching_graph
from agents.state import MatchingState
from config import ROOT_DIR

# Define and create output directories
OUTPUT_DIR = Path(ROOT_DIR) / "backend" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_FILE = OUTPUT_DIR / "phase4_stress_test_report.txt"


async def run_phase4_stress_tests():
    print("=" * 75)
    print("   PHASE 4: ENTERPRISE MULTI-CASE STRESS & ROBUSTNESS TEST SUITE   ")
    print("=" * 75)

    graph = build_clinical_matching_graph()

    # Enterprise Stress Test Matrix covering distinct clinical edge pathways
    stress_cases: List[Dict[str, Any]] = [
        {
            "id": "CASE_1",
            "title": "Clean Melanoma Match (Eligible + High Retention)",
            "patient_id": "PAT_REAL_01",
            "trial_id": "NCT06536257",
            "expected_match": True
        },
        {
            "id": "CASE_2",
            "title": "NSCLC Exclusion (Disqualified + Dynamic Alternative Re-Ranking)",
            "patient_id": "PAT_REAL_02",
            "trial_id": "NCT07182682",
            "expected_match": False
        },
        {
            "id": "CASE_3",
            "title": "Borderline ECOG / Distance Stress Test",
            "patient_id": "PAT_REAL_01",
            "trial_id": "NCT07182682",
            "expected_match": False
        },
        {
            "id": "CASE_4",
            "title": "Indication Mismatch / Safety Contraindication Boundary",
            "patient_id": "PAT_REAL_02",
            "trial_id": "NCT06536257",
            "expected_match": False
        }
    ]

    with open(REPORT_FILE, "w", encoding="utf-8") as out_f:
        out_f.write("=" * 75 + "\n")
        out_f.write("   PHASE 4 ENTERPRISE MULTI-CASE CLINICAL STRESS TEST REPORT\n")
        out_f.write("=" * 75 + "\n\n")

        overall_start_time = time.time()
        passed_assertions = 0

        for i, case in enumerate(stress_cases, 1):
            print(f"\n🧪 [STRESS TEST {i}/{len(stress_cases)}] {case['title']} ({case['patient_id']} vs {case['trial_id']})...")

            initial_state: Dict[str, Any] = {
                "patient_id": case["patient_id"],
                "trial_id": case["trial_id"],
                "patient_context": "",
                "trial_context": "",
                "inclusion_passed": None,
                "inclusion_reasoning": "",
                "exclusion_cleared": None,
                "exclusion_reasoning": "",
                "audit_passed": None,
                "auditor_feedback": "",
                "audit_loop_count": 0,
                "overall_match": False,
                "extraction_confidence": 0.0,
                "eligibility_score": 0.0,
                "confidence_score": 0.0,
                "summary_report": {},
                "error": None,
            }

            start_time = time.time()
            try:
                final_state = await graph.ainvoke(cast(MatchingState, initial_state))
            except Exception as e:
                final_state = {
                    **initial_state,
                    "error": str(e),
                    "summary_report": {"error": f"Execution failure: {str(e)}"}
                }
            elapsed = time.time() - start_time

            summary = final_state.get("summary_report", {}) or {}
            match_result = bool(final_state.get("overall_match", False))
            extraction_conf = summary.get("extraction_confidence", 0.0)
            eligibility_sc = summary.get("eligibility_score", 0.0)
            conf_score = summary.get("confidence_score", 0.0)
            ml_risk = summary.get("ml_attrition_risk", {})
            interventions = ml_risk.get("actionable_interventions", [])
            alternatives = summary.get("alternative_trials", [])

            # Validation assertions
            assertion_passed = (match_result == case["expected_match"])
            if assertion_passed:
                passed_assertions += 1

            status_icon = "✅ PASS" if assertion_passed else "❌ FAIL"
            print(f"{status_icon} Case Completed in {elapsed:.2f}s")
            print(f"   🎯 Overall Match:        {match_result} (Expected: {case['expected_match']})")
            print(f"   🔍 Extraction Conf:      {extraction_conf}")
            print(f"   ⚖️  Eligibility Score:    {eligibility_sc}")
            print(f"   📊 Composite Score:      {conf_score}")
            if match_result:
                print(f"   💡 Retention Strategies: {len(interventions)} actionable tips")
            else:
                print(f"   🔄 Alternatives Found:   {len(alternatives)} trials dynamically re-ranked")
            print("-" * 75)

            # Write formatted output to report file
            out_f.write(f"=== [{case['id']}] {case['title']} ===\n")
            out_f.write(f"Patient ID: {case['patient_id']} | Trial ID: {case['trial_id']}\n")
            out_f.write(f"Execution Latency: {elapsed:.2f} seconds | Test Verdict: {status_icon}\n\n")
            out_f.write("--- INCLUSION REASONING ---\n")
            out_f.write(f"{final_state.get('inclusion_reasoning', 'N/A')}\n\n")
            out_f.write("--- EXCLUSION REASONING ---\n")
            out_f.write(f"{final_state.get('exclusion_reasoning', 'N/A')}\n\n")
            out_f.write("--- AUDITOR AUDIT ---\n")
            out_f.write(f"{final_state.get('auditor_feedback', 'N/A')}\n\n")
            out_f.write("--- SYNTHESIZED DATA PAYLOAD ---\n")
            out_f.write(f"{json.dumps(summary, indent=2)}\n")
            out_f.write("\n" + "=" * 75 + "\n\n")

        overall_elapsed = time.time() - overall_start_time
        accuracy_rate = (passed_assertions / len(stress_cases)) * 100.0

        summary_header = f"""
===========================================================================
   PHASE 4 STRESS TEST EXECUTION SUMMARY
===========================================================================
   Total Cases Evaluated:     {len(stress_cases)}
   Clinical Safety Pass Rate: {passed_assertions}/{len(stress_cases)} ({accuracy_rate:.1f}%)
   Total Batch Duration:      {overall_elapsed:.2f} seconds
   Average Case Latency:      {(overall_elapsed / len(stress_cases)):.2f} seconds/case
   Report File:               {REPORT_FILE}
===========================================================================
"""
        print(summary_header)
        out_f.write(summary_header)


if __name__ == "__main__":
    asyncio.run(run_phase4_stress_tests())