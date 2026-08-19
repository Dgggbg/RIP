"""
MA3AK RAG Accuracy Evaluation
==============================
Tests the RAG system against a set of known clinical questions
and measures: Answer Rate, Confidence Levels, Citation Accuracy,
Hallucination Rate, and Retrieval Similarity Scores.
"""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import sys
import json
import time
sys.path.insert(0, r'c:/Users/Office/RAG')

from query import load_index, retrieve
from generate import generate_grounded_answer

# ── Test Questions (based on WHO Hypertension Guideline 2021) ─────────────────
# Format: (question, expected_confidence, keywords_expected_in_answer)
TEST_CASES = [
    {
        "id": 1,
        "question": "What is the recommended blood pressure target for hypertensive patients?",
        "expected_confidence": ["high", "medium"],
        "must_contain_keywords": ["130", "140", "mmHg", "systolic"],
        "category": "Treatment Target"
    },
    {
        "id": 2,
        "question": "What are the first-line medications for treating hypertension?",
        "expected_confidence": ["high", "medium"],
        "must_contain_keywords": ["ACE", "ARB", "calcium", "diuretic", "thiazide", "beta"],
        "category": "Pharmacotherapy"
    },
    {
        "id": 3,
        "question": "When should drug treatment for hypertension be initiated?",
        "expected_confidence": ["high", "medium"],
        "must_contain_keywords": ["140", "160", "risk", "initiat", "start"],
        "category": "Treatment Initiation"
    },
    {
        "id": 4,
        "question": "What lifestyle modifications are recommended for hypertension management?",
        "expected_confidence": ["high", "medium"],
        "must_contain_keywords": ["salt", "sodium", "exercise", "weight", "alcohol", "diet"],
        "category": "Lifestyle"
    },
    {
        "id": 5,
        "question": "What blood pressure level is defined as hypertension?",
        "expected_confidence": ["high", "medium"],
        "must_contain_keywords": ["140", "90", "mmHg", "define", "grade"],
        "category": "Definition"
    },
    {
        "id": 6,
        "question": "Which patients require additional cardiovascular monitoring?",
        "expected_confidence": ["high", "medium", "low"],
        "must_contain_keywords": ["cardiovascular", "risk", "diabetes", "kidney", "heart"],
        "category": "Risk Stratification"
    },
    {
        "id": 7,
        "question": "What is the role of combination therapy in hypertension?",
        "expected_confidence": ["high", "medium"],
        "must_contain_keywords": ["combination", "two", "drug", "single"],
        "category": "Combination Therapy"
    },
    {
        "id": 8,
        "question": "How should hypertension be managed in elderly patients?",
        "expected_confidence": ["high", "medium", "low"],
        "must_contain_keywords": ["elderly", "older", "age", "65"],
        "category": "Special Populations"
    },
    # Out-of-scope questions (should return insufficient)
    {
        "id": 9,
        "question": "What is the treatment for type 2 diabetes?",
        "expected_confidence": ["insufficient"],
        "must_contain_keywords": [],
        "category": "Out-of-Scope (Diabetes)"
    },
    {
        "id": 10,
        "question": "How is cancer diagnosed?",
        "expected_confidence": ["insufficient"],
        "must_contain_keywords": [],
        "category": "Out-of-Scope (Cancer)"
    },
]

def evaluate():
    print("=" * 65)
    print("   MA3AK RAG ACCURACY EVALUATION")
    print("=" * 65)
    print(f"  Total test cases: {len(TEST_CASES)}")
    print(f"  In-scope questions: {len([t for t in TEST_CASES if 'Out-of-Scope' not in t['category']])}")
    print(f"  Out-of-scope questions: {len([t for t in TEST_CASES if 'Out-of-Scope' in t['category']])}")
    print("=" * 65)

    db = load_index()

    results = []
    total_retrieval_score = 0.0
    answered_correctly = 0
    hallucination_count = 0
    confidence_correct = 0
    keyword_hits = 0
    total_keywords = 0

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {test['category']}")
        print(f"  Q: {test['question'][:70]}...")

        start = time.time()
        retrieved = retrieve(db, test["question"])
        response = generate_grounded_answer(test["question"], retrieved)
        elapsed = time.time() - start

        confidence = response.get("confidence", "unknown")
        recommendation = response.get("recommendation", "")
        citations = response.get("citations", [])

        # Metric 1: Confidence correctness
        conf_correct = confidence in test["expected_confidence"]
        if conf_correct:
            confidence_correct += 1

        # Metric 2: Keyword check (only for in-scope)
        kw_hit = 0
        kw_total = len(test["must_contain_keywords"])
        if kw_total > 0 and confidence != "insufficient":
            answer_lower = recommendation.lower()
            for kw in test["must_contain_keywords"]:
                if kw.lower() in answer_lower:
                    kw_hit += 1
            keyword_hits += kw_hit
            total_keywords += kw_total

        # Metric 3: Retrieval score
        avg_score = sum(s for _, s in retrieved) / len(retrieved) if retrieved else 0
        total_retrieval_score += avg_score

        # Metric 4: Citation integrity
        hallucinated = False
        if citations:
            valid_pages = {doc.metadata.get("page_number") for doc, _ in retrieved}
            for cit in citations:
                if cit.get("page") not in valid_pages:
                    hallucinated = True
                    hallucination_count += 1
                    break

        result = {
            "id": test["id"],
            "category": test["category"],
            "confidence": confidence,
            "confidence_correct": conf_correct,
            "avg_retrieval_score": round(avg_score, 4),
            "keyword_hit_rate": round(kw_hit / kw_total, 2) if kw_total > 0 else "N/A",
            "citations_count": len(citations),
            "hallucinated_citation": hallucinated,
            "response_time_sec": round(elapsed, 2),
            "answer_preview": recommendation[:120] + "..." if len(recommendation) > 120 else recommendation
        }
        results.append(result)

        # Print result
        conf_emoji = "[OK]" if conf_correct else "[FAIL]"
        print(f"  Confidence: {confidence} {conf_emoji}")
        print(f"  Retrieval Score: {avg_score:.4f}")
        if kw_total > 0:
            print(f"  Keywords Found: {kw_hit}/{kw_total}")
        print(f"  Citations: {len(citations)} | Hallucinated: {'[FAIL] YES' if hallucinated else '[OK] NO'}")
        print(f"  Time: {elapsed:.2f}s")

    # ── Final Report ──────────────────────────────────────────────────────────
    in_scope = [r for r in results if "Out-of-Scope" not in r["category"]]
    out_scope = [r for r in results if "Out-of-Scope" in r["category"]]

    print("\n" + "=" * 65)
    print("   FINAL ACCURACY REPORT")
    print("=" * 65)

    conf_acc = (confidence_correct / len(TEST_CASES)) * 100
    kw_acc = (keyword_hits / total_keywords * 100) if total_keywords > 0 else 0
    avg_retrieval = total_retrieval_score / len(TEST_CASES)
    halluc_rate = (hallucination_count / len(TEST_CASES)) * 100
    answered = len([r for r in in_scope if r["confidence"] != "insufficient"])
    answer_rate = (answered / len(in_scope)) * 100
    rejected = len([r for r in out_scope if r["confidence"] == "insufficient"])
    rejection_rate = (rejected / len(out_scope)) * 100

    print(f"\n  [RETRIEVAL] RETRIEVAL")
    print(f"     Avg Similarity Score : {avg_retrieval:.4f} / 1.0")

    print(f"\n  [GENERATION] GENERATION")
    print(f"     Answer Rate (in-scope)   : {answer_rate:.1f}%  ({answered}/{len(in_scope)} questions answered)")
    print(f"     Rejection Rate (OOS)     : {rejection_rate:.1f}%  ({rejected}/{len(out_scope)} out-of-scope rejected)")
    print(f"     Confidence Accuracy      : {conf_acc:.1f}%  ({confidence_correct}/{len(TEST_CASES)} correct)")
    print(f"     Keyword Coverage         : {kw_acc:.1f}%")

    print(f"\n  [HALLUCINATION]  HALLUCINATION GUARD")
    print(f"     Hallucinated Citations   : {hallucination_count}/{len(TEST_CASES)}")
    print(f"     Citation Integrity Rate  : {100 - halluc_rate:.1f}%")

    print(f"\n  [PERFORMANCE] PERFORMANCE")
    avg_time = sum(r["response_time_sec"] for r in results) / len(results)
    print(f"     Avg Response Time        : {avg_time:.2f} seconds")

    # Overall score
    overall = (answer_rate * 0.3 + rejection_rate * 0.2 + conf_acc * 0.2 + kw_acc * 0.2 + (100 - halluc_rate) * 0.1)
    print(f"\n  [SCORE] OVERALL ACCURACY SCORE  : {overall:.1f} / 100")

    if overall >= 80:
        print(f"     Rating: [*****] Excellent")
    elif overall >= 65:
        print(f"     Rating: [****] Good")
    elif overall >= 50:
        print(f"     Rating: [***] Fair")
    else:
        print(f"     Rating: [**] Needs Improvement")

    # Save JSON report
    report = {
        "summary": {
            "total_tests": len(TEST_CASES),
            "answer_rate": f"{answer_rate:.1f}%",
            "rejection_rate": f"{rejection_rate:.1f}%",
            "confidence_accuracy": f"{conf_acc:.1f}%",
            "keyword_coverage": f"{kw_acc:.1f}%",
            "citation_integrity": f"{100 - halluc_rate:.1f}%",
            "avg_retrieval_score": round(avg_retrieval, 4),
            "avg_response_time": f"{avg_time:.2f}s",
            "overall_score": round(overall, 1),
        },
        "details": results
    }

    with open(r"c:/Users/Office/RAG/eval_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n  [FILE] Full report saved to: eval_report.json")
    print("=" * 65)

if __name__ == "__main__":
    evaluate()
