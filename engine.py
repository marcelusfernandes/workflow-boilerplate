"""Shared policy and local evidence engine. Python stdlib only."""
import json
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
from datetime import datetime, timezone
import uuid


class WorkflowError(ValueError):
    """Configuration, policy, or prerequisite failure; never equivalent to passed."""


def validate_config(config, source=None):
    if not isinstance(config, dict) or type(config.get("schema_version")) is not int or config.get("schema_version") != 1:
        raise WorkflowError("Expected config object with schema_version=1.")
    fields = {"schema_version", "project_name", "adapters", "roles", "models", "reasoning_efforts",
              "python_command", "protected_branches", "protected_paths", "owned_paths",
              "evidence_max_age_minutes", "claude_stop_gate", "gates"}
    if set(config) - fields:
        raise WorkflowError("Unknown configuration keys: " + ", ".join(sorted(set(config) - fields)))
    if not isinstance(config.get("project_name"), str) or not config["project_name"].strip():
        raise WorkflowError("project_name must be a nonempty string.")
    if "\n" in config["project_name"] or "\r" in config["project_name"]:
        raise WorkflowError("project_name must be one line.")
    if not isinstance(config.get("adapters"), list) or not config["adapters"]:
        raise WorkflowError("adapters must be a nonempty list.")
    if any(not isinstance(adapter, str) or adapter not in ("codex", "claude") for adapter in config["adapters"]):
        raise WorkflowError("Only codex and claude adapters are supported.")
    source = Path(source or __file__).resolve()
    if source.is_file():
        source = source.parent
    catalog = source / "core/roles.json"
    if not catalog.is_file():
        catalog = source / "roles.json"
    if catalog.resolve() != catalog.absolute():
        raise WorkflowError("Canonical roles file is a symlink/junction.")
    known_roles = json.loads(catalog.read_text(encoding="utf-8"))
    selected = config.get("roles")
    if not isinstance(selected, list) or not selected or any(not isinstance(role, str) or role not in known_roles for role in selected):
        raise WorkflowError("roles must select known canonical roles.")
    if len(set(selected)) != len(selected) or len(set(config["adapters"])) != len(config["adapters"]):
        raise WorkflowError("Duplicate roles or adapters are not allowed.")
    models = config.get("models")
    if not isinstance(models, dict):
        raise WorkflowError("models must contain runtime maps.")
    if set(models) - {"codex", "claude"}:
        raise WorkflowError("Unknown runtime in model selections.")
    for adapter in ("codex", "claude"):
        models.setdefault(adapter, {})
        if not isinstance(models[adapter], dict):
            raise WorkflowError("Model selections must be objects keyed by role.")
        for role, model in models[adapter].items():
            if role not in known_roles or not isinstance(model, str) or not model.strip():
                raise WorkflowError("Model selections require known roles and nonempty model strings.")
    if not isinstance(config.get("reasoning_efforts"), dict):
        raise WorkflowError("reasoning_efforts must be an object.")
    for role, effort in config["reasoning_efforts"].items():
        if role not in known_roles or not isinstance(effort, str) or not effort:
            raise WorkflowError("Invalid reasoning effort selection.")
    if not isinstance(config.get("python_command"), str) or not config["python_command"]:
        raise WorkflowError("python_command must be an executable name/path.")
    if not isinstance(config.get("gates"), list):
        raise WorkflowError("gates must be a list.")
    names = set()
    for gate in config["gates"]:
        if not isinstance(gate, dict) or not isinstance(gate.get("name"), str) or not gate["name"]:
            raise WorkflowError("Each gate needs a nonempty name.")
        if set(gate) - {"name", "argv", "cwd", "timeout_seconds", "result_file"}:
            raise WorkflowError("Unknown gate configuration key.")
        if gate["name"] in names:
            raise WorkflowError("Duplicate gate name.")
        names.add(gate["name"])
        argv = gate.get("argv")
        if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or not a or "\x00" in a for a in argv):
            raise WorkflowError("Gate argv must be a nonempty list of nonempty strings, not shell text.")
        relative_path(gate.get("cwd", "."), allow_dot=True)
        timeout = gate.get("timeout_seconds", 300)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
            raise WorkflowError("Gate timeout_seconds must be between 0 and 3600.")
        if "result_file" in gate:
            relative = relative_path(gate["result_file"])
            if not relative.startswith(".workflow/artifacts/"):
                raise WorkflowError("Gate result_file must be under .workflow/artifacts/.")
            if relative == ".workflow/artifacts/summary.json":
                raise WorkflowError("Gate result_file cannot overwrite runner summary.")
    for key in ("protected_branches", "protected_paths", "owned_paths"):
        if not isinstance(config.get(key), list):
            raise WorkflowError(f"{key} must be a list.")
    for branch in config["protected_branches"]:
        if not isinstance(branch, str) or not branch or re.search(r"[\s~^:?*\[\\]", branch):
            raise WorkflowError("Invalid protected branch name.")
    for pattern in config["protected_paths"]:
        relative_path(pattern)
    for entry in config["owned_paths"]:
        if not isinstance(entry, dict):
            raise WorkflowError("owned_paths entries must be objects.")
        relative_path(entry.get("glob"))
        owners = entry.get("owners")
        if not isinstance(owners, list) or not owners or any(not isinstance(role, str) or role not in known_roles for role in owners):
            raise WorkflowError("owned_paths owners must select known roles.")
    age = config.get("evidence_max_age_minutes")
    if isinstance(age, bool) or not isinstance(age, (int, float)) or not 0 < age <= 10080:
        raise WorkflowError("evidence_max_age_minutes must be between 0 and 10080.")
    if not isinstance(config.get("claude_stop_gate"), bool):
        raise WorkflowError("claude_stop_gate must be boolean.")
    return config


def relative_path(value, allow_dot=False):
    if allow_dot and value == ".":
        return value
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value or ":" in value:
        raise WorkflowError("Paths/globs must be nonempty relative POSIX strings.")
    if value.startswith("/") or any(part in ("", ".", "..") for part in value.split("/")):
        raise WorkflowError("Absolute paths, empty components and traversal are not allowed.")
    return value


def safe_path(root, relative, allow_dot=False):
    relative_path(relative, allow_dot)
    path = root / relative
    if path.resolve() != path.absolute():
        raise WorkflowError(f"Symlink/junction path is not allowed: {relative}")
    if not path.resolve().is_relative_to(root):
        raise WorkflowError(f"Path is outside the worktree: {relative}")
    return path


def matches(path, pattern):
    expression, index = "", 0
    while index < len(pattern):
        if pattern[index:index + 3] == "**/":
            expression += "(?:.*/)?"
            index += 3
        elif pattern[index:index + 2] == "**":
            expression += ".*"
            index += 2
        elif pattern[index] == "*":
            expression += "[^/]*"
            index += 1
        elif pattern[index] == "?":
            expression += "[^/]"
            index += 1
        else:
            expression += re.escape(pattern[index])
            index += 1
    return re.fullmatch(expression, path) is not None


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True)
    if result.returncode:
        raise WorkflowError("Git prerequisite/command failed: " + " ".join(args))
    return result.stdout


def project_root(path):
    path = Path(path).resolve(strict=True)
    return Path(os.fsdecode(git(path, "rev-parse", "--show-toplevel")).strip()).resolve()


def load_config(root):
    path = safe_path(root, ".workflow/config.json")
    config = json.loads(path.read_text(encoding="utf-8"))
    return validate_config(config, safe_path(root, ".workflow"))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def task_contract(root):
    path = safe_path(root, ".workflow/task.json")
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WorkflowError("Task contract must be an object.")
    roles = json.loads(safe_path(root, ".workflow/roles.json").read_text(encoding="utf-8"))
    if not isinstance(value.get("id"), str) or not value["id"] or not isinstance(value.get("owner"), str) or value["owner"] not in roles:
        raise WorkflowError("Task needs a nonempty id and a known owner role.")
    base = value.get("base_ref")
    if not isinstance(base, str) or not base or base.startswith("-") or any(c.isspace() for c in base):
        raise WorkflowError("Task needs an existing Git base_ref.")
    git(root, "rev-parse", "--verify", "--end-of-options", base + "^{commit}")
    patterns = value.get("allowed_globs")
    if not isinstance(patterns, list) or not patterns:
        raise WorkflowError("Task allowed_globs cannot be empty.")
    for pattern in patterns:
        relative_path(pattern)
    return value


def allowed_write(relative, config, task):
    if any(matches(relative, pattern) for pattern in config["protected_paths"]):
        raise WorkflowError(f"Protected path: {relative}")
    if task and not any(matches(relative, pattern) for pattern in task["allowed_globs"]):
        raise WorkflowError(f"Out-of-scope path: {relative}")
    for policy in config["owned_paths"]:
        if matches(relative, policy["glob"]) and (not task or task["owner"] not in policy["owners"]):
            raise WorkflowError(f"Path requires a designated owner: {relative}")


def scope_check(root, config=None):
    config = config or load_config(root)
    task = task_contract(root)
    if not task:
        return {"status": "skipped", "required": False, "reason": "No task contract configured.", "paths": []}
    base = os.fsdecode(git(root, "rev-parse", "--verify", "--end-of-options", task["base_ref"] + "^{commit}")).strip()
    paths = set(os.fsdecode(p) for p in git(root, "diff", "--name-only", "--no-renames", "-z", base, "--").split(b"\0") if p)
    paths.update(os.fsdecode(p) for p in git(root, "diff", "--cached", "--name-only", "--no-renames", "-z", base, "--").split(b"\0") if p)
    paths.update(os.fsdecode(p) for p in git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if p)
    violations = []
    for relative in sorted(paths):
        if relative.startswith(".workflow/artifacts/") or relative == ".workflow/run.lock":
            continue
        try:
            safe_path(root, relative)
            allowed_write(relative, config, task)
        except WorkflowError as error:
            violations.append(str(error))
    return {"status": "failed" if violations else "passed", "required": True,
            "base": base, "owner": task["owner"], "paths": sorted(paths), "violations": violations}


def fingerprint(root, config):
    paths = set(os.fsdecode(p) for p in git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0") if p)
    records = []
    for relative in sorted(paths):
        if relative.startswith(".workflow/artifacts/") or relative == ".workflow/run.lock":
            continue
        if "__pycache__" in relative.split("/") or relative.endswith(".pyc"):
            continue
        if any(matches(relative, pattern) for pattern in config["protected_paths"]):
            raise WorkflowError(f"Protected file cannot be included in evidence: {relative}")
        path = safe_path(root, relative)
        if path.is_file():
            content = hashlib.sha256(path.read_bytes()).hexdigest()
            mode = path.stat().st_mode & 0o111
            records.append([relative, content, mode])
        elif not path.exists():
            records.append([relative, "deleted"])
        else:
            raise WorkflowError(f"Unsupported Git entry (directory/submodule): {relative}")
    index = git(root, "ls-files", "--stage", "-z")
    for entry in index.split(b"\0"):
        if entry and entry.partition(b"\t")[0].split()[-1] != b"0":
            raise WorkflowError("Unmerged Git index is not valid evidence.")
    task = task_contract(root)
    base = os.fsdecode(git(root, "rev-parse", "--verify", "--end-of-options", task["base_ref"] + "^{commit}")).strip() if task else None
    return {"head": os.fsdecode(git(root, "rev-parse", "HEAD")).strip(),
            "content": digest(records), "index": hashlib.sha256(index).hexdigest(),
            "config": digest(config), "task": digest(task), "base": base}


def save_summary(root, summary):
    path = safe_path(root, ".workflow/artifacts/summary.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = safe_path(root, ".workflow/artifacts/summary.pending.json")
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run_gate(root, gate):
    started = time.monotonic()
    record = {"name": gate["name"], "argv": gate["argv"], "cwd": gate.get("cwd", "."),
              "status": "blocked", "exit_code": None, "reason": "", "seconds": 0}
    try:
        cwd = safe_path(root, gate.get("cwd", "."), allow_dot=True)
        if not cwd.is_dir():
            raise WorkflowError("Gate working directory is unavailable.")
        result_path = None
        if "result_file" in gate:
            result_path = safe_path(root, gate["result_file"])
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.unlink(missing_ok=True)
        completed = subprocess.run(gate["argv"], cwd=cwd, timeout=gate.get("timeout_seconds", 300),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        record["exit_code"] = completed.returncode
        record["status"] = "passed" if completed.returncode == 0 else "failed"
        if completed.returncode:
            record["reason"] = "Command returned a nonzero exit code; rerun directly for diagnostics."
        if completed.returncode == 0 and result_path:
            result_path = safe_path(root, gate["result_file"])
            data = json.loads(result_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("status") not in ("passed", "failed", "skipped", "blocked", "error"):
                raise WorkflowError("Invalid structured gate status.")
            counts = [data.get(key) for key in ("total", "failed", "skipped")]
            if any(type(value) is not int or value < 0 for value in counts) or counts[1] + counts[2] > counts[0]:
                raise WorkflowError("Invalid structured gate counts.")
            if data["status"] == "passed" and (counts[0] == 0 or counts[1] or counts[2]):
                raise WorkflowError("Structured passed requires tests > 0, zero failed and zero skipped.")
            record.update({key: data[key] for key in ("status", "total", "failed", "skipped")})
            record["reason"] = str(data.get("reason", ""))
    except subprocess.TimeoutExpired:
        record.update(status="blocked", reason="Gate exceeded timeout.")
    except OSError:
        record.update(status="blocked", reason="Executable, cwd, or result file is unavailable.")
    except ValueError as error:
        record.update(status="error", reason=str(error))
    record["seconds"] = round(time.monotonic() - started, 3)
    return record


def run_gates(root):
    config = load_config(root)
    lock_path = safe_path(root, ".workflow/run.lock")
    try:
        lock = lock_path.open("x")
    except FileExistsError as error:
        raise WorkflowError("A workflow run lock exists; confirm its owner before cleanup.") from error
    try:
        with lock:
            lock.write(str(os.getpid()))
        state = fingerprint(root, config)
        summary = {"schema_version": 1, "run_id": str(uuid.uuid4()), "ok": False,
                   "started_at": datetime.now(timezone.utc).isoformat(), "fingerprint": state,
                   "gates": [], "limits": ["Command exit codes are not test counts without result_file.",
                                            "Ignored files, native runtime activation, CI and independent review are not proven."]}
        save_summary(root, summary)
        summary["scope"] = scope_check(root, config)
        if summary["scope"]["status"] == "failed":
            summary["reason"] = "Task scope/ownership failed; gates were not executed."
        elif not config["gates"]:
            summary["reason"] = "No gates configured; not passed."
        else:
            summary["gates"] = [run_gate(root, gate) for gate in config["gates"]]
            summary["ok"] = all(gate["status"] == "passed" for gate in summary["gates"])
        after = fingerprint(root, load_config(root))
        if state != after:
            summary.update(ok=False, reason="Worktree content, HEAD or configuration changed during the gates.")
        summary["finished_at"] = datetime.now(timezone.utc).isoformat()
        save_summary(root, summary)
        return summary
    finally:
        lock_path.unlink(missing_ok=True)


def check_evidence(root):
    config = load_config(root)
    if safe_path(root, ".workflow/run.lock").exists():
        raise WorkflowError("Evidence is unavailable while a workflow run lock exists.")
    summary = json.loads(safe_path(root, ".workflow/artifacts/summary.json").read_text(encoding="utf-8"))
    if not isinstance(summary, dict) or summary.get("schema_version") != 1 or summary.get("ok") is not True:
        raise WorkflowError("Evidence schema/status is invalid or not passed.")
    gates = summary.get("gates")
    if not isinstance(gates, list) or not gates or len(gates) != len(config["gates"]):
        raise WorkflowError("Evidence gate count does not match configured gates.")
    for result, expected in zip(gates, config["gates"]):
        if not isinstance(result, dict) or result.get("status") != "passed" or result.get("exit_code") != 0:
            raise WorkflowError("Evidence contains a malformed or non-passed gate.")
        if result.get("name") != expected["name"] or result.get("argv") != expected["argv"] or result.get("cwd") != expected.get("cwd", "."):
            raise WorkflowError("Evidence gate identity/command differs from configuration.")
        if "result_file" in expected:
            counts = [result.get(key) for key in ("total", "failed", "skipped")]
            if any(type(value) is not int for value in counts) or counts[0] <= 0 or counts[1] != 0 or counts[2] != 0:
                raise WorkflowError("Evidence structured gate counts are not passed.")
    if summary.get("scope") != scope_check(root, config):
        raise WorkflowError("Evidence scope is invalid or stale.")
    if not isinstance(summary.get("finished_at"), str):
        raise WorkflowError("Evidence timestamp is invalid.")
    current = fingerprint(root, config)
    if current != summary.get("fingerprint"):
        raise WorkflowError("Evidence HEAD/content/config/task is stale; rerun gates.")
    finished = datetime.fromisoformat(summary["finished_at"])
    if finished.tzinfo is None:
        raise WorkflowError("Evidence timestamp must contain a timezone.")
    age = (datetime.now(timezone.utc) - finished).total_seconds()
    if not 0 <= age <= config["evidence_max_age_minutes"] * 60:
        raise WorkflowError("Evidence timestamp is expired or in the future.")
    return summary


def pre_hook(root, payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("cwd"), str):
        raise WorkflowError("Invalid hook input; cwd is required.")
    if project_root(payload["cwd"]) != root:
        raise WorkflowError("Hook cwd does not belong to this worktree.")
    tool = payload.get("tool_name")
    data = payload.get("tool_input")
    if not isinstance(data, dict):
        raise WorkflowError("Invalid hook tool_input.")
    config = load_config(root)
    if tool in ("Write", "Edit", "MultiEdit"):
        value = data.get("file_path")
        if not isinstance(value, str) or not value:
            raise WorkflowError("Write/Edit hook requires file_path.")
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = Path(payload["cwd"]) / candidate
        candidate = Path(os.path.abspath(candidate))
        if not candidate.is_relative_to(root):
            raise WorkflowError("Write target is outside this worktree.")
        relative = candidate.relative_to(root).as_posix()
        safe_path(root, relative)
        task = task_contract(root)
        if task:
            roles = json.loads(safe_path(root, ".workflow/roles.json").read_text(encoding="utf-8"))
            if roles[task["owner"]]["read_only"]:
                raise WorkflowError("The declared task owner is read-only.")
        allowed_write(relative, config, task)
    elif tool == "Bash":
        command = data.get("command")
        if not isinstance(command, str) or not command or "\x00" in command:
            raise WorkflowError("Bash hook requires a nonempty command.")
        patterns = [r"\bgit\b[^;&|\n]*\b(?:stash|clean)\b", r"\bgit\b[^;&|\n]*\breset\b[^;&|\n]*--hard\b",
                    r"\bgit\b[^;&|\n]*\bpush\b[^;&|\n]*(?:--force(?:-with-lease)?\b|(?:^|\s)-[A-Za-z]*f[A-Za-z]*(?:\s|$))",
                    r"\bgh\b[^;&|\n]*\bpr\s+merge\b", r"\bgh\b[^;&|\n]*\brepo\s+delete\b"]
        if any(re.search(pattern, command) for pattern in patterns):
            raise WorkflowError("Destructive Git/history or remote integration command is blocked by the local guard.")
        push = re.search(r"\bgit\b[^;&|\n]*\bpush\b([^;&|\n]*)", command)
        if push:
            branch = os.fsdecode(git(root, "branch", "--show-current")).strip()
            if branch in config["protected_branches"] or any(re.search(r"(?<![\w/])(?:refs/heads/)?" + re.escape(name) + r"(?![\w/])", push.group(1)) for name in config["protected_branches"]):
                raise WorkflowError("Push to a protected branch is blocked; integration requires an authorized operation outside the agent guard.")
    else:
        raise WorkflowError("Unsupported tool for the configured PreToolUse guard.")


def hook(root, event, stream):
    try:
        payload = json.load(stream)
        if event == "pre":
            pre_hook(root, payload)
        else:
            if not isinstance(payload, dict) or not isinstance(payload.get("stop_hook_active", False), bool):
                raise WorkflowError("Invalid Stop hook input.")
            if payload.get("stop_hook_active"):
                return 0
            try:
                check_evidence(root)
            except (ValueError, OSError) as error:
                print(json.dumps({"decision": "block", "reason": "Run required workflow gates before claiming completion: " + str(error)}))
        return 0
    except (ValueError, OSError) as error:
        import sys
        print("Workflow guard denied: " + str(error), file=sys.stderr)
        return 2


def pre_push(root, stream):
    config = load_config(root)
    for line in stream:
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 4:
            raise WorkflowError("Malformed Git pre-push input; refused.")
        local_ref, local_sha, remote_ref, remote_sha = fields
        if not remote_ref.startswith("refs/") or any(not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha) for sha in (local_sha, remote_sha)):
            raise WorkflowError("Invalid ref/SHA in Git pre-push input.")
        if remote_ref in {"refs/heads/" + branch for branch in config["protected_branches"]}:
            raise WorkflowError("Push/delete of protected destination refused: " + remote_ref)
        if set(local_sha) == {"0"} or set(remote_sha) == {"0"}:
            continue
        result = subprocess.run(["git", "merge-base", "--is-ancestor", remote_sha, local_sha], cwd=root,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode:
            raise WorkflowError("Non-fast-forward update or unavailable ancestry refused: " + remote_ref)
    return 0


def install_git_hook(root, apply=False):
    config = load_config(root)
    custom = subprocess.run(["git", "config", "--get", "core.hooksPath"], cwd=root, capture_output=True, text=True)
    if custom.stdout.strip():
        raise WorkflowError("core.hooksPath is configured; integrate with the existing hook manager manually.")
    hooks = Path(os.fsdecode(git(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks")).strip())
    hooks = Path(os.path.abspath(hooks))
    if hooks.resolve() != hooks:
        raise WorkflowError("Symlink/junction hooks directory is not supported.")
    path = hooks / "pre-push"
    command = shlex.quote(config["python_command"])
    content = ('#!/usr/bin/env sh\n# workflow-boilerplate pre-push v1\n'
               'root="$(git rev-parse --show-toplevel)" || exit 1\n'
               f'exec {command} "$root/.workflow/workflow.py" git-pre-push "$@"\n').encode()
    if path.is_symlink() or (path.exists() and (not path.is_file() or path.read_bytes() != content)):
        raise WorkflowError("Existing pre-push hook conflicts; no hook was changed.")
    unchanged = path.exists()
    print(json.dumps({"mode": "apply" if apply else "preview", "path": str(path),
                      "unchanged": unchanged, "scope": "Git hooks directory; may be shared by linked worktrees"}, indent=2))
    if apply:
        if not unchanged:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(content)
        path.chmod(path.stat().st_mode | 0o111)
    return 0
