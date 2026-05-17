#!/usr/bin/env python3
import argparse
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


def summarize_pip_audit(data) -> tuple[int, int]:
    if not data:
        return 0, 0
    deps = data.get("dependencies", [])
    vuln_count = 0
    for dep in deps:
        vuln_count += len(dep.get("vulns", []))
    return len(deps), vuln_count


def summarize_bandit(data) -> tuple[int, dict]:
    if not data:
        return 0, {}
    results = data.get("results", [])
    sev = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for item in results:
        s = (item.get("issue_severity") or "").upper()
        if s in sev:
            sev[s] += 1
    return len(results), sev


def summarize_semgrep(data) -> tuple[int, dict]:
    if not data:
        return 0, {}
    results = data.get("results", [])
    sev = {"INFO": 0, "WARNING": 0, "ERROR": 0}
    for item in results:
        extra = item.get("extra", {})
        s = (extra.get("severity") or "").upper()
        if s in sev:
            sev[s] += 1
    return len(results), sev


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize OWASP scan JSON reports")
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

    pip_data = load_json(report_dir / "pip-audit.json")
    bandit_data = load_json(report_dir / "bandit.json")
    semgrep_data = load_json(report_dir / "semgrep.json")

    deps_scanned, pip_vulns = summarize_pip_audit(pip_data)
    bandit_total, bandit_sev = summarize_bandit(bandit_data)
    semgrep_total, semgrep_sev = summarize_semgrep(semgrep_data)

    print("OWASP Security Scan Summary")
    print("=" * 28)
    print(f"Report directory: {report_dir}")
    print()

    print("Dependency Scan (pip-audit)")
    if pip_data is None:
        print("- Status: report missing or unreadable")
    else:
        print(f"- Dependencies scanned: {deps_scanned}")
        print(f"- Vulnerabilities found: {pip_vulns}")
    print()

    print("Static Analysis (bandit)")
    if bandit_data is None:
        print("- Status: report missing or unreadable")
    else:
        print(f"- Findings: {bandit_total}")
        print(
            "- Severity breakdown: "
            f"LOW={bandit_sev.get('LOW', 0)}, "
            f"MEDIUM={bandit_sev.get('MEDIUM', 0)}, "
            f"HIGH={bandit_sev.get('HIGH', 0)}"
        )
    print()

    print("Static Analysis (semgrep)")
    if semgrep_data is None:
        print("- Status: report missing or unreadable")
    else:
        print(f"- Findings: {semgrep_total}")
        print(
            "- Severity breakdown: "
            f"INFO={semgrep_sev.get('INFO', 0)}, "
            f"WARNING={semgrep_sev.get('WARNING', 0)}, "
            f"ERROR={semgrep_sev.get('ERROR', 0)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
