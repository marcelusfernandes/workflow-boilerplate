"""Independent acceptance and edge cases; no production, secrets or remote requests."""
from datetime import datetime, timedelta, timezone
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tomllib
import unittest
from unittest.mock import patch as mock_patch

from test_workflow import WorkflowCase, ROOT


class SafetyTests(WorkflowCase):
    def test_static_validation_and_doctor_do_not_install_files(self):
        result = self.cli("validate")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["canonical_roles"], 9)
        self.assertEqual(report["canonical_skills"], 7)
        doctor = self.cli("doctor")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertFalse(json.loads(doctor.stdout)["side_effects"])
        self.assertFalse((self.repo / ".workflow").exists())

    def update_config(self, **values):
        path = self.repo / ".workflow/config.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config.update(values)
        path.write_text(json.dumps(config), encoding="utf-8")

    def passing_gate(self):
        self.configure_gates([{"name": "command", "argv": [sys.executable, "-c", "assert True"]}])

    def snapshot(self):
        self.git("add", ".")
        self.git("-c", "core.hooksPath=", "commit", "-m", "Synthetic baseline")

    def set_task(self, patterns, owner="implementador", base="HEAD"):
        task = {"id": "local/fixture", "owner": owner, "base_ref": base, "allowed_globs": patterns}
        (self.repo / ".workflow/task.json").write_text(json.dumps(task), encoding="utf-8")

    def test_existing_instructions_conflict_is_atomic(self):
        (self.repo / "AGENTS.md").write_text("Existing user instructions\n", encoding="utf-8")
        result = self.cli("install", "--target", str(self.repo), "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("conflict", result.stderr.lower())
        self.assertFalse((self.repo / ".workflow").exists())
        self.assertEqual((self.repo / "AGENTS.md").read_text(encoding="utf-8"), "Existing user instructions\n")

    def test_existing_hook_and_custom_hook_manager_are_preserved(self):
        self.install()
        hook = self.repo / ".git/hooks/pre-push"
        hook.write_text("#!/bin/sh\n# Existing hook\n", encoding="utf-8")
        result = self.runtime("install-git-hook", "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Existing hook", hook.read_text(encoding="utf-8"))
        self.git("config", "core.hooksPath", ".custom-hooks")
        result = self.runtime("install-git-hook", "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("core.hooksPath", result.stderr)
        self.assertFalse((self.repo / ".custom-hooks").exists())

    def test_empty_gates_missing_executable_and_timeout_never_pass(self):
        self.install()
        self.assertNotEqual(self.runtime("run").returncode, 0)
        cases = [
            {"name": "missing", "argv": ["workflow-synthetic-executable-does-not-exist"]},
            {"name": "timeout", "argv": [sys.executable, "-c", "import time; time.sleep(5)"], "timeout_seconds": 0.05},
        ]
        for gate in cases:
            with self.subTest(gate=gate["name"]):
                self.configure_gates([gate])
                self.assertNotEqual(self.runtime("run").returncode, 0)
                data = json.loads((self.repo / ".workflow/artifacts/summary.json").read_text(encoding="utf-8"))
                self.assertFalse(data["ok"])
                self.assertEqual(data["gates"][0]["status"], "blocked")

    def test_structured_results_reject_zero_tests_skips_and_missing_reports(self):
        self.install()
        result_file = ".workflow/artifacts/test-result.json"
        cases = [
            {"status": "passed", "total": 0, "failed": 0, "skipped": 0},
            {"status": "passed", "total": 3, "failed": 0, "skipped": 1},
            {"status": "skipped", "total": 3, "failed": 0, "skipped": 3},
            {"status": "passed", "total": 2, "failed": 0, "skipped": 0},
        ]
        for data in cases:
            with self.subTest(data=data):
                code = "import pathlib; pathlib.Path(" + repr(result_file) + ").write_text(" + repr(json.dumps(data)) + ")"
                self.configure_gates([{"name": "reported", "argv": [sys.executable, "-c", code], "result_file": result_file}])
                result = self.runtime("run")
                valid = data == cases[-1]
                self.assertEqual(result.returncode == 0, valid, result.stdout + result.stderr)
        self.configure_gates([{"name": "missing-result", "argv": [sys.executable, "-c", "assert True"], "result_file": result_file}])
        self.assertNotEqual(self.runtime("run").returncode, 0)
        self.assertFalse((self.repo / result_file).exists(), "An old gate report must not be reused")

    def test_changed_head_task_and_expired_evidence_are_rejected(self):
        self.install()
        self.passing_gate()
        self.assertEqual(self.runtime("run").returncode, 0)
        self.git("-c", "core.hooksPath=", "commit", "--allow-empty", "-m", "Synthetic new HEAD")
        self.assertNotEqual(self.runtime("check-evidence").returncode, 0)
        self.assertEqual(self.runtime("run").returncode, 0)
        self.set_task(["**"])
        self.assertNotEqual(self.runtime("check-evidence").returncode, 0)
        self.assertEqual(self.runtime("run").returncode, 0)
        report = self.repo / ".workflow/artifacts/summary.json"
        data = json.loads(report.read_text(encoding="utf-8"))
        data["finished_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        report.write_text(json.dumps(data), encoding="utf-8")
        self.assertNotEqual(self.runtime("check-evidence").returncode, 0)

    def test_lock_and_source_mutation_during_gate_are_not_green(self):
        self.install()
        self.passing_gate()
        lock = self.repo / ".workflow/run.lock"
        lock.write_text("synthetic owner", encoding="utf-8")
        self.assertNotEqual(self.runtime("run").returncode, 0)
        self.assertEqual(lock.read_text(encoding="utf-8"), "synthetic owner")
        lock.unlink()
        code = "from pathlib import Path; Path('source.txt').write_text('changed by synthetic gate')"
        self.configure_gates([{"name": "mutating", "argv": [sys.executable, "-c", code]}])
        self.assertNotEqual(self.runtime("run").returncode, 0)
        self.assertNotEqual(self.runtime("check-evidence").returncode, 0)
        self.assertFalse(lock.exists())

    def test_scope_covers_staged_unstaged_untracked_delete_and_rename(self):
        self.install()
        self.snapshot()
        self.set_task(["source.txt", "tests/**/*.txt"])
        nested = self.repo / "tests/nested"
        nested.mkdir(parents=True)
        (nested / "ação with spaces.txt").write_text("synthetic", encoding="utf-8")
        (self.repo / "tests/root.txt").write_text("synthetic", encoding="utf-8")
        (self.repo / "source.txt").write_text("unstaged", encoding="utf-8")
        self.assertEqual(self.runtime("scope").returncode, 0)
        self.git("add", "source.txt")
        self.assertEqual(self.runtime("scope").returncode, 0)
        (self.repo / "source.txt").unlink()
        self.assertEqual(self.runtime("scope").returncode, 0)
        (self.repo / "source.txt").write_text("synthetic\n", encoding="utf-8")
        self.git("mv", "source.txt", "renamed outside.txt")
        denied = self.runtime("scope")
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("renamed outside.txt", denied.stdout + denied.stderr)
        self.assertIn("source.txt", denied.stdout)

    def test_owner_policy_outside_paths_and_stop_recursion(self):
        self.install()
        self.update_config(owned_paths=[{"glob": "source.txt", "owners": ["banco"]}])
        self.set_task(["**"])
        payload = {"cwd": str(self.repo), "tool_name": "Write", "tool_input": {"file_path": str(self.repo / "source.txt")}}
        self.assertEqual(self.runtime("hook", "pre", input=json.dumps(payload)).returncode, 2)
        payload["tool_input"]["file_path"] = str(Path(self.temp.name) / "outside.txt")
        self.assertEqual(self.runtime("hook", "pre", input=json.dumps(payload)).returncode, 2)
        result = self.runtime("hook", "stop", input=json.dumps({"stop_hook_active": False}))
        self.assertEqual(json.loads(result.stdout)["decision"], "block")
        repeated = self.runtime("hook", "stop", input=json.dumps({"stop_hook_active": True}))
        self.assertEqual(repeated.returncode, 0)
        self.assertEqual(repeated.stdout, "")

    def test_malformed_task_owner_fails_closed_in_hook(self):
        self.install()
        self.set_task(["**"], owner={"not": "a string"})
        payload = {"cwd": str(self.repo), "tool_name": "Write", "tool_input": {"file_path": str(self.repo / "source.txt")}}
        result = self.runtime("hook", "pre", input=json.dumps(payload))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unknown_configuration_keys_are_rejected_without_partial_install(self):
        self.config.write_text(json.dumps({"project_name": "Synthetic", "gatez": []}), encoding="utf-8")
        result = self.cli("install", "--target", str(self.repo), "--config", str(self.config), "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.repo / ".workflow").exists())

    def test_parent_file_collision_does_not_partially_install(self):
        (self.repo / ".agents").write_text("Existing user file", encoding="utf-8")
        result = self.cli("install", "--target", str(self.repo), "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.repo / ".workflow").exists())
        self.assertFalse((self.repo / "AGENTS.md").exists())
        self.assertEqual((self.repo / ".agents").read_text(encoding="utf-8"), "Existing user file")

    def test_corrupt_evidence_record_is_not_accepted(self):
        self.install()
        self.passing_gate()
        self.assertEqual(self.runtime("run").returncode, 0)
        path = self.repo / ".workflow/artifacts/summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))
        summary["gates"] = [{"status": "passed"}]
        path.write_text(json.dumps(summary), encoding="utf-8")
        result = self.runtime("check-evidence")
        self.assertNotEqual(result.returncode, 0)
        stop = self.runtime("hook", "stop", input=json.dumps({"stop_hook_active": False}))
        self.assertEqual(json.loads(stop.stdout)["decision"], "block")

    def test_existing_worktree_uses_shared_hook_dir_without_changing_base_files(self):
        self.install()
        self.snapshot()
        linked = Path(self.temp.name) / "linked synthetic worktree"
        self.git("worktree", "add", "-b", "feature/linked", str(linked))
        command = [sys.executable, str(linked / ".workflow/workflow.py"), "install-git-hook", "--apply"]
        result = subprocess.run(command, cwd=linked, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.repo / ".git/hooks/pre-push").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertFalse((linked / ".workflow/artifacts").exists())

    def test_all_optional_profiles_validate_and_preserve_explicit_models(self):
        roles = json.loads((ROOT / "core/roles.json").read_text(encoding="utf-8"))
        self.config.write_text(json.dumps({"project_name": "Synthetic", "roles": list(roles),
            "models": {"codex": {"revisor": "user-selected-model"}, "claude": {"qa": "user-selected-model"}},
            "reasoning_efforts": {"revisor": "high"}}), encoding="utf-8")
        self.install()
        for name in roles:
            data = tomllib.loads((self.repo / f".codex/agents/{name}.toml").read_text(encoding="utf-8"))
            self.assertEqual(data["name"], name)
            self.assertEqual(data["developer_instructions"], roles[name]["instructions"])
            if name != "revisor":
                self.assertNotIn("model", data)
        review = tomllib.loads((self.repo / ".codex/agents/revisor.toml").read_text(encoding="utf-8"))
        self.assertEqual(review["model"], "user-selected-model")
        self.assertIn('model: "user-selected-model"', (self.repo / ".claude/agents/qa.md").read_text(encoding="utf-8"))

    def test_index_only_changes_are_out_of_scope(self):
        self.install()
        self.passing_gate()
        self.snapshot()
        self.set_task(["tests/**"])
        self.assertEqual(self.runtime("run").returncode, 0)
        (self.repo / "source.txt").write_text("synthetic untested index bytes\n", encoding="utf-8")
        self.git("add", "source.txt")
        (self.repo / "source.txt").write_text("synthetic\n", encoding="utf-8")
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "source.txt")
        denied = self.runtime("scope")
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("source.txt", denied.stdout)

    def test_index_only_changes_invalidate_evidence_without_task(self):
        self.install()
        self.passing_gate()
        self.snapshot()
        self.assertEqual(self.runtime("run").returncode, 0)
        (self.repo / "source.txt").write_text("synthetic untested index bytes\n", encoding="utf-8")
        self.git("add", "source.txt")
        (self.repo / "source.txt").write_text("synthetic\n", encoding="utf-8")
        self.assertNotEqual(self.runtime("check-evidence").returncode, 0)

    def test_moved_named_base_during_gate_cannot_produce_passed_summary(self):
        self.install()
        code = "import subprocess; subprocess.run(['git','update-ref','refs/heads/task-base','HEAD^'],check=True)"
        self.configure_gates([{"name": "move-base", "argv": [sys.executable, "-c", code]}])
        self.snapshot()
        self.git("branch", "task-base")
        self.set_task(["**"], base="task-base")
        result = self.runtime("run")
        self.assertNotEqual(result.returncode, 0)
        summary = json.loads((self.repo / ".workflow/artifacts/summary.json").read_text(encoding="utf-8"))
        self.assertFalse(summary["ok"])
        self.assertNotEqual(self.runtime("check-evidence").returncode, 0)

    def test_malformed_summary_blocks_stop_with_structured_error(self):
        self.install()
        self.passing_gate()
        self.assertEqual(self.runtime("run").returncode, 0)
        path = self.repo / ".workflow/artifacts/summary.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        missing_time = dict(original)
        missing_time.pop("finished_at")
        for invalid in ([], {"ok": True, "gates": ["passed"]}, missing_time):
            with self.subTest(invalid=invalid):
                path.write_text(json.dumps(invalid), encoding="utf-8")
                result = self.runtime("hook", "stop", input="{}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["decision"], "block")
                self.assertNotIn("Traceback", result.stderr)

    def test_apply_rechecks_parent_swapped_after_directory_creation(self):
        import installer
        outside = Path(self.temp.name) / "concurrent synthetic outside"
        outside.mkdir()
        workflow_dir = self.repo / ".workflow"
        original_mkdir = Path.mkdir
        swapped = False

        def swap_after_mkdir(path, *args, **kwargs):
            nonlocal swapped
            original_mkdir(path, *args, **kwargs)
            if path == workflow_dir and not swapped:
                swapped = True
                workflow_dir.rmdir()
                if sys.platform == "win32":
                    result = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(workflow_dir), str(outside)], capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    workflow_dir.symlink_to(outside, target_is_directory=True)

        with mock_patch.object(Path, "mkdir", swap_after_mkdir), redirect_stdout(io.StringIO()):
            with self.assertRaises((ValueError, OSError)):
                installer.install(self.repo, self.config, apply=True)
        self.assertTrue(swapped)
        self.assertEqual(list(outside.iterdir()), [])

    def test_gate_replacing_result_directory_with_junction_is_rejected(self):
        self.install()
        outside = Path(self.temp.name) / "synthetic gate outside"
        outside.mkdir()
        sentinel = "EXTERNAL_SYNTHETIC_REPORT_NOT_TO_BE_READ"
        (outside / "result.json").write_text(json.dumps({"status": "passed", "total": 1, "failed": 0, "skipped": 0, "reason": sentinel}), encoding="utf-8")
        result_dir = self.repo / ".workflow/artifacts/redirect"
        if sys.platform == "win32":
            code = "import pathlib,subprocess; p=pathlib.Path(" + repr(str(result_dir)) + "); p.rmdir(); subprocess.run(['cmd.exe','/c','mklink','/J',str(p)," + repr(str(outside)) + "],check=True)"
        else:
            code = "import pathlib; p=pathlib.Path(" + repr(str(result_dir)) + "); p.rmdir(); p.symlink_to(" + repr(str(outside)) + ",target_is_directory=True)"
        self.configure_gates([{"name": "redirect", "argv": [sys.executable, "-c", code], "result_file": ".workflow/artifacts/redirect/result.json"}])
        result = self.runtime("run")
        self.assertNotEqual(result.returncode, 0)
        summary = (self.repo / ".workflow/artifacts/summary.json").read_text(encoding="utf-8")
        self.assertNotIn(sentinel, summary)
        self.assertFalse(json.loads(summary)["ok"])

    def test_junction_or_symlink_escape_is_rejected_before_write(self):
        self.install()
        outside = Path(self.temp.name) / "outside synthetic"
        outside.mkdir()
        link = self.repo / "escape"
        if sys.platform == "win32":
            created = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True, text=True, errors="replace")
            self.assertEqual(created.returncode, 0, created.stderr + created.stdout)
        else:
            link.symlink_to(outside, target_is_directory=True)
        payload = {"cwd": str(self.repo), "tool_name": "Write", "tool_input": {"file_path": str(link / "do-not-create.txt")}}
        denied = self.runtime("hook", "pre", input=json.dumps(payload))
        self.assertEqual(denied.returncode, 2, denied.stderr)
        self.assertIn("Symlink/junction", denied.stderr)
        self.assertFalse((outside / "do-not-create.txt").exists())


if __name__ == "__main__":
    unittest.main()
