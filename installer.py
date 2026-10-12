"""Distribution installer. Preview first; never overwrite conflicting files."""
import json
from pathlib import Path
import shlex
import subprocess


class WorkflowError(ValueError):
    """An explicit configuration, policy, or prerequisite failure."""


def git_root(path):
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path,
                            capture_output=True, text=True)
    if result.returncode:
        raise WorkflowError("Target must be an existing Git repository; no git init is performed.")
    return Path(result.stdout.strip()).resolve()


def render_files(config, source):
    roles = json.loads((source / "core/roles.json").read_text(encoding="utf-8"))
    files = {
        ".workflow/workflow.py": (source / "workflow.py").read_bytes(),
        ".workflow/engine.py": (source / "engine.py").read_bytes(),
        ".workflow/roles.json": (source / "core/roles.json").read_bytes(),
        ".workflow/config.json": (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode(),
    }
    template_map = {
        "AGENTS.md": "core/AGENTS.md", "CLAUDE.md": "core/CLAUDE.md",
        ".workflow/project.md": "core/project.md",
        ".workflow/docs/orchestration.md": "core/orchestration.md",
        ".workflow/docs/adapters.md": "docs/adapters.md",
        ".workflow/docs/configuration.md": "docs/configuration.md",
        ".workflow/memory/MEMORY.md": "core/memory.md",
        ".workflow/task.example.json": "core/task.example.json",
        ".workflow/.gitignore": "core/workflow.gitignore",
    }
    if "claude" not in config["adapters"]:
        template_map.pop("CLAUDE.md")
    for destination, relative in template_map.items():
        text = (source / relative).read_text(encoding="utf-8")
        files[destination] = text.replace("{{PROJECT_NAME}}", config["project_name"]).encode()
    for path in sorted((source / "core/skills").glob("*/SKILL.md")):
        if "codex" in config["adapters"]:
            files[f".agents/skills/{path.parent.name}/SKILL.md"] = path.read_bytes()
        if "claude" in config["adapters"]:
            files[f".claude/skills/{path.parent.name}/SKILL.md"] = path.read_bytes()
    for name in config["roles"]:
        role = roles[name]
        instruction = role["instructions"]
        if "codex" in config["adapters"]:
            lines = [f"name = {json.dumps(name)}", f"description = {json.dumps(role['description'], ensure_ascii=False)}"]
            model = config["models"]["codex"].get(name)
            if model:
                lines.append(f"model = {json.dumps(model)}")
            effort = config["reasoning_efforts"].get(name)
            if effort:
                lines.append(f"model_reasoning_effort = {json.dumps(effort)}")
            lines.append(f"sandbox_mode = {json.dumps('read-only' if role['read_only'] else 'workspace-write')}")
            lines.append(f"developer_instructions = {json.dumps(instruction, ensure_ascii=False)}")
            files[f".codex/agents/{name}.toml"] = ("\n".join(lines) + "\n").encode()
        if "claude" in config["adapters"]:
            lines = ["---", f"name: {name}", f"description: {json.dumps(role['description'], ensure_ascii=False)}",
                     f"model: {json.dumps(config['models']['claude'].get(name, 'inherit'))}"]
            if role["read_only"]:
                lines.append("tools: Read, Grep, Glob, Bash")
                lines.append("disallowedTools: Write, Edit, NotebookEdit")
            lines.append("skills: " + json.dumps(role["skills"]))
            lines.extend(["---", "", instruction, ""])
            files[f".claude/agents/{name}.md"] = "\n".join(lines).encode()
    if "claude" in config["adapters"]:
        command = shlex.quote(config["python_command"]) + ' "${CLAUDE_PROJECT_DIR}/.workflow/workflow.py" hook '
        hooks = {"PreToolUse": [{"matcher": "Bash|Edit|Write|MultiEdit", "hooks": [
            {"type": "command", "command": command + "pre", "timeout": 15, "onFailure": "block"}
        ]}]}
        if config["claude_stop_gate"]:
            hooks["Stop"] = [{"hooks": [{"type": "command", "command": command + "stop",
                                          "timeout": 15, "onFailure": "block"}]}]
        files[".claude/settings.json"] = (json.dumps({"hooks": hooks}, indent=2) + "\n").encode()
    return files


def install(target, config_path, apply=False):
    from engine import validate_config, safe_path
    source = Path(__file__).resolve().parent
    target = Path(target).resolve(strict=True)
    if git_root(target) != target:
        raise WorkflowError("Target must be the Git worktree root, not a nested directory.")
    config = json.loads((source / "config.example.json").read_text(encoding="utf-8"))
    if config_path:
        overrides = json.loads(Path(config_path).read_text(encoding="utf-8"))
        if not isinstance(overrides, dict):
            raise WorkflowError("Config must be a JSON object.")
        config.update(overrides)
    validate_config(config, source)
    files = render_files(config, source)
    changes, conflicts = [], []
    for relative, content in files.items():
        path = target / relative
        parent = path.parent
        while parent != target:
            if parent.exists() and not parent.is_dir():
                conflicts.append(relative + " (ancestor is an existing file)")
                break
            parent = parent.parent
        if path.resolve() != path.absolute():
            raise WorkflowError(f"Symlink/junction destination is not allowed: {relative}")
        if path.exists():
            if not path.is_file() or path.read_bytes() != content:
                conflicts.append(relative)
        else:
            changes.append(relative)
    if conflicts:
        raise WorkflowError("Installation conflicts; no files were changed: " + ", ".join(conflicts))
    print(json.dumps({"mode": "apply" if apply else "preview", "target": str(target),
                      "create": changes, "unchanged": len(files) - len(changes),
                      "git_hooks_installed": False}, ensure_ascii=False, indent=2))
    if apply:
        created = []
        for relative in changes:
            try:
                path = safe_path(target, relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                path = safe_path(target, relative)
                with path.open("xb") as handle:
                    safe_path(target, relative)
                    handle.write(files[relative])
                created.append(relative)
            except (ValueError, OSError) as error:
                raise WorkflowError("Installation interrupted; created files before interruption: " +
                                    json.dumps(created) + "; reason: " + str(error)) from error
    return 0
