"""Run evaluation suite against the LLM."""

import asyncio
import json
import os

from services.grammar_service import GrammarService


async def run_eval(cases_path: str = "evals/eval_cases.json", output_path: str = "evals/eval_results.json"):
    with open(cases_path) as f:
        cases = json.load(f)

    svc = GrammarService()
    results = []

    for case in cases:
        try:
            result = await svc.check(case["input"])
            errors = result.get("errors", [])
            expected = case.get("expected_errors", [])

            # Simple heuristic: count-based match for now
            status = "pass" if len(errors) >= len(expected) else "fail"

            results.append({
                "id": case["id"],
                "description": case["description"],
                "status": status,
                "errors_found": errors,
                "expected_count": len(expected),
            })
        except Exception as e:
            results.append({
                "id": case["id"],
                "description": case["description"],
                "status": "error",
                "errors_found": [],
                "expected_count": len(case.get("expected_errors", [])),
                "error": str(e),
            })

    await svc.close()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    passed = sum(1 for r in results if r["status"] == "pass")
    print(f"Eval complete: {passed}/{len(results)} passed")
    return results


if __name__ == "__main__":
    asyncio.run(run_eval())
