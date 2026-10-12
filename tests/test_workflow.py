"""Offline integration tests using disposable Git repositories and synthetic data."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "workflow.py"


class WorkflowCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-", dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "synthetic project with spaces"
        self.repo.mkdir()
        self.git("init", "-b", "feature/example")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.git("config", "core.autocrlf", "false")
        (self.repo / "source.txt").write_text("synthetic\n", encoding="utf-8")
        self.git("add", "source.txt")
        self.git("-c", "core.hooksPath=", "commit", "-m", "Synthetic fixture")
        self.config = Path(self.temp.name) / "config.json"
        self.config.write_text(json.dumps({"project_name": "Synthetic project"}), encoding="utf-8")

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.repo, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def cli(self, *args, input=None):
        return subprocess.run([sys.executable, str(CLI), *args], cwd=self.repo,
                              input=input, text=True, capture_output=True)

    def install(self):
        result = self.cli("install", "--target", str(self.repo), "--config", str(self.config), "--apply")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def runtime(self, *args, input=None):
        return subprocess.run([sys.executable, str(self.repo / ".workflow/workflow.py"), *args],
                              cwd=self.repo, input=input, text=True, capture_output=True)

    def configure_gates(self, gates):
        path = self.repo / ".workflow/config.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config["gates"] = gates
        path.write_text(json.dumps(config), encoding="utf-8")


class WorkflowTests(WorkflowCase):
    def test_scope_contract_and_claude_guard_are_enforced(self):
        self.install()
        self.configure_gates([{"name": "unit", "argv": [sys.executable, "-c", "assert True"]}])
        self.git("add", ".")
        self.git("-c", "core.hooksPath=", "commit", "-m", "Synthetic workflow baseline")
        task = {"id": "local/fixture", "owner": "implementador", "base_ref": "HEAD",
                "allowed_globs": ["source.txt", "tests/**"]}
        (self.repo / ".workflow/task.json").write_text(json.dumps(task), encoding="utf-8")
        (self.repo / "source.txt").write_text("allowed change\n", encoding="utf-8")
        permitted = self.runtime("scope")
        self.assertEqual(permitted.returncode, 0, permitted.stderr)
        payload = {"cwd": str(self.repo), "tool_name": "Write",
                   "tool_input": {"file_path": str(self.repo / "source.txt")}}
        self.assertEqual(self.runtime("hook", "pre", input=json.dumps(payload)).returncode, 0)
        payload["tool_input"]["file_path"] = str(self.repo / ".env.local")
        self.assertEqual(self.runtime("hook", "pre", input=json.dumps(payload)).returncode, 2)
        malformed = self.runtime("hook", "pre", input="not json")
        self.assertEqual(malformed.returncode, 2)
        payload = {"cwd": str(self.repo), "tool_name": "Bash",
                   "tool_input": {"command": "git reset --hard HEAD"}}
        self.assertEqual(self.runtime("hook", "pre", input=json.dumps(payload)).returncode, 2)
        (self.repo / "outside.txt").write_text("out of scope\n", encoding="utf-8")
        denied = self.runtime("scope")
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("outside.txt", denied.stdout + denied.stderr)
        blocked_run = self.runtime("run")
        self.assertNotEqual(blocked_run.returncode, 0)

    def test_installed_git_hook_blocks_protected_destination_in_real_local_push(self):
        self.install()
        preview = self.runtime("install-git-hook")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse((self.repo / ".git/hooks/pre-push").exists())
        installed = self.runtime("install-git-hook", "--apply")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.assertEqual(self.runtime("install-git-hook", "--apply").returncode, 0)
        bare = Path(self.temp.name) / "synthetic remote.git"
        created = subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, text=True)
        self.assertEqual(created.returncode, 0, created.stderr)
        self.git("remote", "add", "synthetic", str(bare))
        self.git("push", "synthetic", "HEAD:refs/heads/feature/example")
        denied = subprocess.run(["git", "push", "synthetic", "HEAD:refs/heads/main"],
                                cwd=self.repo, capture_output=True, text=True)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("protected", denied.stderr.lower())
        remote_check = subprocess.run(["git", "--git-dir", str(bare), "show-ref", "--verify", "refs/heads/main"], capture_output=True)
        self.assertNotEqual(remote_check.returncode, 0)
        sha = self.git("rev-parse", "HEAD")
        orphan = self.git("commit-tree", "HEAD^{tree}", "-m", "Synthetic divergent commit")
        update = f"refs/heads/diverged {orphan} refs/heads/feature/example {sha}\n"
        rejected = self.runtime("git-pre-push", input=update)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("fast-forward", rejected.stderr)

    def test_real_gates_failures_and_content_freshness(self):
        self.install()
        self.configure_gates([{"name": "unit", "argv": [sys.executable, "-c", "assert True"]}])
        passed = self.runtime("run")
        self.assertEqual(passed.returncode, 0, passed.stderr + passed.stdout)
        self.assertEqual(self.runtime("check-evidence").returncode, 0)
        (self.repo / "source.txt").write_text("changed\n", encoding="utf-8")
        stale = self.runtime("check-evidence")
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("content", stale.stderr.lower())
        self.configure_gates([{"name": "unit", "argv": [sys.executable, "-c", "raise SystemExit(7)"]}])
        failed = self.runtime("run")
        self.assertNotEqual(failed.returncode, 0)
        summary = json.loads((self.repo / ".workflow/artifacts/summary.json").read_text(encoding="utf-8"))
        self.assertFalse(summary["ok"])
        self.assertEqual(summary["gates"][0]["status"], "failed")
        self.assertEqual(summary["gates"][0]["exit_code"], 7)
        self.assertNotEqual(self.runtime("check-evidence").returncode, 0)

    def test_install_preview_apply_and_idempotence(self):
        preview = self.cli("install", "--target", str(self.repo), "--config", str(self.config))
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse((self.repo / ".workflow").exists())
        self.install()
        self.assertTrue((self.repo / ".workflow/workflow.py").is_file())
        self.assertTrue((self.repo / "AGENTS.md").is_file())
        installed = json.loads((self.repo / ".workflow/config.json").read_text(encoding="utf-8"))
        self.assertEqual(installed["project_name"], "Synthetic project")
        repeat = self.cli("install", "--target", str(self.repo), "--config", str(self.config), "--apply")
        self.assertEqual(repeat.returncode, 0, repeat.stderr)
        self.assertFalse((self.repo / ".git/hooks/pre-push").exists())


if __name__ == "__main__":
    unittest.main()
