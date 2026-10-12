"""Portable development workflow CLI, Python 3.11+ and Git."""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    install_parser = subparsers.add_parser("install", help="Preview or apply project-local files")
    install_parser.add_argument("--target", required=True)
    install_parser.add_argument("--config")
    install_parser.add_argument("--apply", action="store_true")
    for name in ("run", "check-evidence", "scope"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--root", default=".")
    hook_parser = subparsers.add_parser("hook")
    hook_parser.add_argument("event", choices=("pre", "stop"))
    hook_parser.add_argument("--root", default=".")
    git_parser = subparsers.add_parser("git-pre-push")
    git_parser.add_argument("remote", nargs="*")
    git_parser.add_argument("--root", default=".")
    git_install_parser = subparsers.add_parser("install-git-hook")
    git_install_parser.add_argument("--root", default=".")
    git_install_parser.add_argument("--apply", action="store_true")
    validation_parser = subparsers.add_parser("validate", help="Validate distribution sources without writing")
    validation_parser.add_argument("--config")
    doctor_parser = subparsers.add_parser("doctor", help="Read-only prerequisite discovery")
    doctor_parser.add_argument("--root", default=".")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            from validation import validate_distribution
            print(json.dumps(validate_distribution(args.config), ensure_ascii=False, indent=2))
            return 0
        if args.command == "doctor" and (Path(__file__).resolve().parent / "core").is_dir():
            from validation import doctor_distribution
            report = doctor_distribution()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "install":
            from installer import install
            return install(args.target, args.config, args.apply)
        from engine import project_root, run_gates, check_evidence, scope_check, hook, pre_push, install_git_hook
        root = project_root(args.root)
        if args.command == "doctor":
            from engine import load_config
            config = load_config(root)
            report = {"status": "passed" if config["gates"] else "blocked", "python": sys.version.split()[0],
                      "root": str(root), "gates": len(config["gates"]), "task_configured": (root / ".workflow/task.json").exists(),
                      "side_effects": False, "limits": ["No gates executed and no client/runtime activation checked."]}
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["status"] == "passed" else 1
        if args.command == "git-pre-push":
            return pre_push(root, sys.stdin)
        if args.command == "install-git-hook":
            return install_git_hook(root, args.apply)
        if args.command == "hook":
            return hook(root, args.event, sys.stdin)
        if args.command == "scope":
            result = scope_check(root)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1 if result["status"] == "failed" else 0
        if args.command == "run":
            summary = run_gates(root)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0 if summary["ok"] else 1
        if args.command == "check-evidence":
            summary = check_evidence(root)
            print(json.dumps({"status": "passed", "run_id": summary["run_id"], "fingerprint": summary["fingerprint"]}))
            return 0
    except (ValueError, OSError, ImportError) as error:
        print(json.dumps({"status": "error", "reason": str(error)}), file=sys.stderr)
        return 2 if args.command == "hook" else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
