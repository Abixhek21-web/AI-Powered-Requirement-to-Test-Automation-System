import os
import argparse
import json
import re
from src.ingestion import load_documents, split_documents
from src.retriever import HybridRetriever
from src.generator import TestGenerator
from src.evaluator import Evaluator
from src.feedback_handler import FeedbackHandler

def main():
    parser = argparse.ArgumentParser(description="AI Test Generator Evaluation Pipeline")
    parser.add_argument("--data", default="data/input", help="Path to requirement documents or directory")
    parser.add_argument("--query", default="Generate all functional test cases for this requirement", help="Evaluation query")
    parser.add_argument("--output", default="evaluation_report.md", help="Path to save the report")
    args = parser.parse_args()

    print(f"[*] Starting evaluation on: {args.data}")
    
    # 1. Load Context
    docs = load_documents(args.data)
    if not docs:
        print("[!] No documents found.")
        return
    
    chunks = split_documents(docs)
    retriever = HybridRetriever(chunks)
    generator = TestGenerator(retriever)
    evaluator = Evaluator()
    feedback = FeedbackHandler()

    full_text = " ".join([doc.page_content for doc in docs])

    # 3. Generate
    print("[*] Generating Test Cases...")
    test_cases = generator.generate_test_cases(args.query)
    
    print("[*] Generating Script...")
    script = generator.generate_automation_script(test_cases)

    # 4. Evaluate (Audit Mode)
    print("[*] Running Evaluation Metrics (Audit Mode)...")
    syntax_valid = evaluator.validate_python_syntax(script)
    rtm_results = evaluator.verify_rtm_mapping(test_cases, script)
    pom_results = evaluator.check_pom_compliance(script)
    resource_results = evaluator.check_resource_leaks(script)
    ai_eval = evaluator.ai_judge_evaluation(args.query, full_text[:2000], test_cases)

    # 5. Generate Report
    report = f"""# AI Test Generator Audit Report

## 1. Summary
- **Source Data**: `{args.data}`
- **Evaluation Query**: `{args.query}`
- **Overall Quality (Judge)**: {ai_eval.get('summary', 'N/A')}

## 2. Compliance & RTM Audit
| Metric | Result | Details |
| :--- | :--- | :--- |
| **Python Syntax** | {"✅ Pass" if syntax_valid else "❌ Fail"} | {"Valid script." if syntax_valid else "Syntax errors detected."} |
| **RTM Coverage** | {rtm_results['rtm_coverage_score']}% | Mapped {len(rtm_results['mapped_ids'])} IDs. |
| **POM Compliance** | {pom_results['score']}% | {"Highly Compliant" if pom_results['compliant'] else "Non-Compliant"} |
| **Resource Safety** | {"✅ Safe" if resource_results['safe'] else "❌ Leak Risk"} | {resource_results['details']} |

## 3. Qualitative Evaluation (AI Judge)
- **Groundedness**: {ai_eval.get('groundedness', 0)}/5
- **Coverage**: {ai_eval.get('coverage', 0)}/5
- **Clarity**: {ai_eval.get('clarity', 0)}/5

## 4. Traceability Mapping
- **Mapped IDs**: `{", ".join(rtm_results['mapped_ids'])}`
- **Missing IDs**: `{", ".join(rtm_results['missing_ids'])}`
"""
    
    if not syntax_valid or rtm_results['rtm_coverage_score'] < 50:
        feedback.log_failure("CLI_EVAL_FAILURE", f"Poor metrics for query: {args.query}")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"[+] Evaluation complete. Report saved to {args.output}")

if __name__ == "__main__":
    main()
