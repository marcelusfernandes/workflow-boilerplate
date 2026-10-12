"""Static validation of the canonical catalog and generated runtime adapters."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

from engine import WorkflowError, validate_config
from installer import render_files


def frontmatter(text):
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise WorkflowError("Invalid Markdown frontmatter.")
    header, body = text[4:].split("\n---\n", 1)
    values = {}
    for line in header.splitlines():
        key, separator, value = line.partition(":")
        if not separator or key in values:
            raise WorkflowError("Invalid or duplicate frontmatter field.")
        value = value.strip()
        values[key] = json.loads(value) if value.startswith(('"', '[')) else value
    if not values.get("name") or not values.get("description") or not body.strip():
        raise WorkflowError("Frontmatter requires name, description and a body.")
    return values, body.strip()


def validate_distribution(config_path=None):
    source = Path(__file__).resolve().parent
    config = json.loads((source / "config.example.json").read_text(encoding="utf-8"))
    if config_path:
        overrides = json.loads(Path(config_path).read_text(encoding="utf-8"))
        if not isinstance(overrides, dict):
            raise WorkflowError("Config overrides must be an object.")
        config.update(overrides)
    validate_config(config, source)
    roles = json.loads((source / "core/roles.json").read_text(encoding="utf-8"))
    skills = {}
    for path in sorted((source / "core/skills").glob("*/SKILL.md")):
        data, body = frontmatter(path.read_text(encoding="utf-8"))
        if data["name"] != path.parent.name or len(data["description"]) > 60:
            raise WorkflowError("Skill name/description is invalid: " + str(path.relative_to(source)))
        for required in ("## Quando usar", "## Armadilhas", "## Verificação"):
            if required not in body:
                raise WorkflowError("Skill missing section: " + data["name"] + " " + required)
        skills[data["name"]] = path.read_bytes()
    for name, role in roles.items():
        if not isinstance(role.get("read_only"), bool) or not role.get("instructions") or not role.get("description"):
            raise WorkflowError("Invalid canonical role: " + name)
        if any(skill not in skills for skill in role["skills"]):
            raise WorkflowError("Role references missing skill: " + name)
    files = render_files(config, source)
    agents = 0
    for path, content in files.items():
        if path.startswith(".codex/agents/"):
            data = tomllib.loads(content.decode())
            if data["developer_instructions"] != roles[data["name"]]["instructions"]:
                raise WorkflowError("Codex role drift: " + path)
            agents += 1
        elif path.startswith(".claude/agents/"):
            data, body = frontmatter(content.decode())
            if body != roles[data["name"]]["instructions"]:
                raise WorkflowError("Claude role drift: " + path)
            agents += 1
        elif path.endswith("SKILL.md"):
            name = Path(path).parent.name
            if content != skills[name]:
                raise WorkflowError("Skill adapter drift: " + path)
        elif path.endswith(".json"):
            json.loads(content)
    return {"status": "passed", "canonical_roles": len(roles), "canonical_skills": len(skills),
            "selected_roles": len(config["roles"]), "adapters": config["adapters"],
            "generated_agents": agents, "generated_files": len(files),
            "limits": ["Static validation only; no client/runtime or model activation claimed."]}


def doctor_distribution():
    git = shutil.which("git")
    version = subprocess.run([git, "--version"], capture_output=True, text=True).stdout.strip() if git else None
    return {"status": "passed" if git and sys.version_info >= (3, 11) else "blocked",
            "python": sys.version.split()[0], "git": version, "side_effects": False,
            "distribution": validate_distribution()}
