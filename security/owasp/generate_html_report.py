#!/usr/bin/env python3
import argparse
import html
import json
from pathlib import Path


def latest_report_dir(reports_root: Path) -> Path | None:
    dirs = [p for p in reports_root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    return sorted(dirs)[-1]


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarize_pip_audit(data):
    if not data:
        return 0, 0, []
    deps = data.get("dependencies", [])
    vuln_rows = []
    vuln_count = 0
    for dep in deps:
        name = dep.get("name", "unknown")
        version = dep.get("version", "")
        for v in dep.get("vulns", []):
            vuln_count += 1
            vuln_rows.append(
                {
                    "package": name,
                    "version": version,
                    "id": v.get("id", ""),
                    "fix_versions": ", ".join(v.get("fix_versions", [])),
                    "description": (v.get("description") or "").strip(),
                }
            )
    return len(deps), vuln_count, vuln_rows


def summarize_bandit(data):
    if not data:
        return 0, {"LOW": 0, "MEDIUM": 0, "HIGH": 0}, []
    results = data.get("results", [])
    sev = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    rows = []
    for item in results:
        s = (item.get("issue_severity") or "").upper()
        if s in sev:
            sev[s] += 1
        rows.append(
            {
                "severity": s or "UNKNOWN",
                "confidence": item.get("issue_confidence", ""),
                "file": item.get("filename", ""),
                "line": item.get("line_number", ""),
                "test_id": item.get("test_id", ""),
                "text": item.get("issue_text", ""),
            }
        )
    return len(results), sev, rows


def summarize_semgrep(data):
    if not data:
        return 0, {"INFO": 0, "WARNING": 0, "ERROR": 0}, []
    results = data.get("results", [])
    sev = {"INFO": 0, "WARNING": 0, "ERROR": 0}
    rows = []
    for item in results:
        extra = item.get("extra", {})
        s = (extra.get("severity") or "").upper()
        if s in sev:
            sev[s] += 1
        rows.append(
            {
                "severity": s or "UNKNOWN",
                "check_id": item.get("check_id", ""),
                "path": item.get("path", ""),
                "line": (item.get("start") or {}).get("line", ""),
                "message": extra.get("message", ""),
            }
        )
    return len(results), sev, rows


def table_from_rows(headers, rows):
    if not rows:
        return "<p class='ok'>No findings.</p>"

    head = "".join([f"<th>{html.escape(h)}</th>" for h in headers])
    body_rows = []
    for row in rows:
        cols = "".join([f"<td>{html.escape(str(row.get(k, '')))}</td>" for k in headers])
        body_rows.append(f"<tr>{cols}</tr>")
    body = "".join(body_rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_html(report_dir: Path, output_file: Path):
    pip_data = load_json(report_dir / "pip-audit.json")
    bandit_data = load_json(report_dir / "bandit.json")
    semgrep_data = load_json(report_dir / "semgrep.json")

    deps_scanned, pip_vulns, pip_rows = summarize_pip_audit(pip_data)
    bandit_total, bandit_sev, bandit_rows = summarize_bandit(bandit_data)
    semgrep_total, semgrep_sev, semgrep_rows = summarize_semgrep(semgrep_data)

    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>OWASP Scan Summary</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ margin-bottom: 8px; }}
    h2 {{ margin-top: 28px; }}
    .muted {{ color: #6b7280; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-top: 14px; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; background: #f9fafb; }}
    .metric {{ font-size: 1.6rem; font-weight: 700; margin-top: 2px; }}
    .ok {{ color: #047857; font-weight: 600; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 0.92rem; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>OWASP Security Report</h1>
  <p class=\"muted\">Source directory: {html.escape(str(report_dir))}</p>

  <div class=\"cards\">
    <div class=\"card\"><div>Dependencies scanned</div><div class=\"metric\">{deps_scanned}</div></div>
    <div class=\"card\"><div>pip-audit vulns</div><div class=\"metric\">{pip_vulns}</div></div>
    <div class=\"card\"><div>Bandit findings</div><div class=\"metric\">{bandit_total}</div></div>
    <div class=\"card\"><div>Semgrep findings</div><div class=\"metric\">{semgrep_total}</div></div>
  </div>

  <h2>pip-audit</h2>
  <p>Vulnerabilities found: <strong>{pip_vulns}</strong></p>
  {table_from_rows(["package", "version", "id", "fix_versions", "description"], pip_rows)}

  <h2>Bandit</h2>
  <p>Findings: <strong>{bandit_total}</strong> (LOW={bandit_sev['LOW']}, MEDIUM={bandit_sev['MEDIUM']}, HIGH={bandit_sev['HIGH']})</p>
  {table_from_rows(["severity", "confidence", "file", "line", "test_id", "text"], bandit_rows)}

  <h2>Semgrep</h2>
  <p>Findings: <strong>{semgrep_total}</strong> (INFO={semgrep_sev['INFO']}, WARNING={semgrep_sev['WARNING']}, ERROR={semgrep_sev['ERROR']})</p>
  {table_from_rows(["severity", "check_id", "path", "line", "message"], semgrep_rows)}
</body>
</html>
"""

    output_file.write_text(html_doc, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate browser-friendly HTML from OWASP JSON reports")
    parser.add_argument(
        "report_dir",
        nargs="?",
        default="",
        help="Path to timestamped security report directory (defaults to latest under security/reports)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    reports_root = repo_root / "security" / "reports"

    if args.report_dir:
        report_dir = Path(args.report_dir).resolve()
    else:
        report_dir = latest_report_dir(reports_root)
        if report_dir is None:
            print("No report directories found under security/reports")
            return 1

    output_file = report_dir / "owasp-summary.html"
    render_html(report_dir, output_file)
    print(f"HTML report generated: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
