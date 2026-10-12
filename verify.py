"""Run offline acceptance tests and write an actual, content-bound verification report."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import unittest

from validation import validate_distribution

ROOT = Path(__file__).resolve().parent


def distribution_fingerprint():
    files = []
    for directory in ("core", "docs", "examples", "extensions", "adapters", "tests"):
        files.extend(path for path in (ROOT / directory).rglob("*") if path.is_file()
                     and "__pycache__" not in path.parts and path.suffix != ".pyc")
    files.extend(ROOT / name for name in ("workflow.py", "installer.py", "engine.py", "validation.py",
                                          "verify.py", "README.md", "config.example.json", ".gitignore", ".gitattributes"))
    entries = []
    for path in sorted(set(files)):
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError("Distribution source path is a symlink or outside the root.")
        entries.append({"file": path.relative_to(ROOT).as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    content = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    return {"sha256": content, "files": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="verification.json", help="JSON basename under artifacts/")
    args = parser.parse_args()
    if "/" in args.report or "\\" in args.report or ":" in args.report or not args.report.endswith(".json"):
        parser.error("--report must be a JSON basename, not a path.")
    started = datetime.now(timezone.utc).isoformat()
    static = validate_distribution()
    before = distribution_fingerprint()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = distribution_fingerprint()
    passed = result.wasSuccessful() and result.testsRun > 0 and not result.skipped and before == after
    report = {"schema_version": 1, "ok": passed, "status": "passed" if passed else "failed",
              "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
              "platform": platform.platform(), "python": sys.version.split()[0],
              "total": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "failed_tests": [str(test) for test, _ in result.failures + result.errors],
              "source_changed_during_tests": before != after, "fingerprint": before,
              "static": static, "limits": ["No native Codex/Claude activation, remote CI or other OS execution claimed.",
                                            "Tests install/push only into disposable synthetic local repositories."]}
    path = ROOT / "artifacts" / args.report
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "total": report["total"], "failures": report["failures"],
                      "errors": report["errors"], "skipped": report["skipped"],
                      "sha256": before["sha256"], "report": str(path)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
