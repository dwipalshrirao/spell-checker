"""Generate a static HTML eval report from eval results."""

import json
import os

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GrammarCheck — Eval Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ color: #333; }}
  .pass {{ color: #16a34a; font-weight: bold; }}
  .fail {{ color: #dc2626; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
  th, td {{ padding: 0.5rem; text-align: left; border-bottom: 1px solid #ddd; }}
  th {{ background: #f5f5f5; }}
  tr:hover {{ background: #f9f9f9; }}
  .summary {{ font-size: 1.2rem; margin: 1rem 0; }}
  .detail {{ background: #f5f5f5; padding: 0.75rem; border-radius: 4px; margin: 0.25rem 0; font-size: 0.9rem; }}
</style>
</head>
<body>
<h1>GrammarCheck — Evaluation Report</h1>
<div class="summary">Passed: <span class="pass">{passed}</span> / {total} &mdash; Score: <strong>{pct:.1f}%</strong></div>
<table>
<tr><th>ID</th><th>Description</th><th>Status</th><th>Errors Found</th><th>Errors Expected</th></tr>
{rows}
</table>
</body>
</html>
"""


def generate_report(results: list[dict], output_path: str = "eval_report.html"):
    passed = sum(1 for r in results if r["status"] == "pass")
    total = len(results)
    pct = (passed / total * 100) if total else 0.0

    rows = []
    for r in results:
        status = '<span class="pass">PASS</span>' if r["status"] == "pass" else '<span class="fail">FAIL</span>'
        err_detail = "<br>".join(
            f'<div class="detail">{e.get("original", "?")} → {e.get("corrected", "?")} '
            f'({e.get("type", "?")})</div>'
            for e in r.get("errors_found", [])
        ) or "<em>none</em>"
        rows.append(
            f"<tr><td>{r['id']}</td><td>{r['description']}</td>"
            f"<td>{status}</td><td>{err_detail}</td>"
            f"<td>{r['expected_count']}</td></tr>"
        )

    html = HTML_TEMPLATE.format(passed=passed, total=total, pct=pct, rows="\n".join(rows))
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Eval report written to {output_path}")


if __name__ == "__main__":
    import sys
    results_path = sys.argv[1] if len(sys.argv) > 1 else "eval_results.json"
    with open(results_path) as f:
        results = json.load(f)
    generate_report(results)
