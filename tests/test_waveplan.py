"""Behavioral, negative, non-execution and deterministic tests; stdlib only."""
import ast
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("waveplan", ROOT / "scripts" / "waveplan.py")
waveplan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(waveplan)


class Base(unittest.TestCase):
    def setUp(self):
        self.plan = waveplan.load_json(ROOT / "examples" / "plan.json")

    def bad(self, code, change):
        plan = deepcopy(self.plan)
        change(plan)
        with self.assertRaises(waveplan.PlanError) as caught:
            waveplan.validate_plan(plan)
        self.assertEqual(code, caught.exception.code)
        self.assertTrue(caught.exception.path)
        self.assertTrue(caught.exception.hint)

    def report(self, status="DONE"):
        task = self.plan["tasks"][0]
        return {"plan_digest": waveplan.canonical_digest(self.plan), "task_id": task["id"], "status": status,
                "files_touched": task["files_allowed"][:], "verification": [{"command": task["verification"]["green"]["command"], "exit_code": 0, "summary": "Worker claims all tests passed."}],
                "acceptance_passed": [item["id"] for item in task["acceptance"]], "notes": []}

    def independent(self):
        plan = deepcopy(self.plan)
        plan["interfaces"] = []
        for task in plan["tasks"]:
            task["depends_on"], task["consumes"], task["produces"], task["files_read"] = [], [], [], []
        return plan

    def invoke(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = waveplan.main(argv)
        return code, out.getvalue(), err.getvalue()


class ValidationTests(Base):
    def test_example_is_valid_and_has_three_waves(self):
        self.assertIs(self.plan, waveplan.validate_plan(self.plan))
        self.assertEqual([["T1", "T2"], ["T3"], ["T4"]], [item["tasks"] for item in waveplan.schedule_plan(self.plan)["waves"]])

    def test_missing_explicit_fields(self):
        for field in waveplan.PLAN_FIELDS:
            with self.subTest(field=field):
                self.bad("MISSING_FIELD", lambda plan: plan.pop(field))
        for field in waveplan.TASK_FIELDS:
            with self.subTest(task_field=field):
                self.bad("MISSING_FIELD", lambda plan: plan["tasks"][0].pop(field))

    def test_unknown_fields_are_rejected(self):
        self.bad("UNKNOWN_FIELD", lambda plan: plan.update({"wave": 1}))
        self.bad("UNKNOWN_FIELD", lambda plan: plan["tasks"][0].update({"status": "DONE"}))
        self.bad("UNKNOWN_FIELD", lambda plan: plan["tasks"][0]["verification"]["green"].update({"execute": True}))

    def test_numeric_bounds_and_bool(self):
        for value in (0, 6, True, False, 3.0, "3", None):
            with self.subTest(value=value):
                self.bad("RANGE", lambda plan: plan.update(max_parallel=value))
        for value in (0, 61, True, 1.5):
            with self.subTest(timeout=value):
                self.bad("RANGE", lambda plan: plan["tasks"][0]["verification"]["green"].update(timeout_seconds=value))

    def test_versions_and_profiles(self):
        self.bad("VERSION", lambda plan: plan.update(schema_version="2.0"))
        for value in ("opus", [], None):
            self.bad("PROFILE", lambda plan: plan["tasks"][0].update(profile=value))

    def test_duplicate_ids_and_entries(self):
        self.bad("DUPLICATE", lambda plan: plan["tasks"].append(deepcopy(plan["tasks"][0])))
        self.bad("DUPLICATE", lambda plan: plan["interfaces"].append(deepcopy(plan["interfaces"][0])))
        self.bad("DUPLICATE", lambda plan: plan["requirements"].append(deepcopy(plan["requirements"][0])))
        self.bad("DUPLICATE", lambda plan: plan["tasks"][2]["depends_on"].append("T1"))
        self.bad("DUPLICATE", lambda plan: plan["tasks"][0]["resources"].extend(["shared", "shared"]))
        self.bad("DUPLICATE", lambda plan: plan["tasks"][0]["files_allowed"].append("SAMPLE/normalization.py"))

    def test_empty_positive_negative_and_global_scope(self):
        for field in ("contains", "does_not_contain"):
            self.bad("TYPE", lambda plan: plan["tasks"][0]["functions"][0].update({field: []}))
        self.bad("TYPE", lambda plan: plan.update(anti_scope=[]))
        self.bad("TYPE", lambda plan: plan["tasks"][0].update(acceptance=[]))
        self.bad("TYPE", lambda plan: plan.update(goal="   "))

    def test_coverage_and_unknown_references(self):
        self.bad("COVERAGE", lambda plan: plan["requirements"].append({"id": "R99", "text": "Uncovered requirement"}))
        self.bad("COVERAGE", lambda plan: plan["decisions"].append({"id": "D99", "text": "Uncovered decision"}))
        self.bad("UNKNOWN_REFERENCE", lambda plan: plan["tasks"][0]["requirement_ids"].append("R99"))
        self.bad("UNKNOWN_REFERENCE", lambda plan: plan["tasks"][0]["decision_ids"].append("D99"))

    def test_red_null_requires_reason(self):
        self.bad("TYPE", lambda plan: plan["tasks"][0]["verification"].update(red=None, red_reason=""))
        self.plan["tasks"][0]["verification"].update(red=None, red_reason="Read-only contract assertion; no implementation change required.")
        waveplan.validate_plan(self.plan)

    def test_text_and_identifier_hardening(self):
        for value in ("x\x00y", "x\x1by", "x\u202ey", "x\ud800y"):
            self.bad("TEXT_CONTROL", lambda plan: plan.update(goal=value))
        self.bad("ID", lambda plan: plan["tasks"][0].update(id="../T1"))
        self.bad("ID", lambda plan: plan.update(plan_id="Uppercase"))

    def test_function_exact_allowed_file(self):
        self.bad("FUNCTION_SCOPE", lambda plan: plan["tasks"][0]["functions"][0].update(file="sample/other.py"))
        self.bad("FUNCTION_SCOPE", lambda plan: plan["tasks"][0]["functions"][0].update(file="SAMPLE/normalization.py"))

    def test_wrong_container_types_are_diagnostics(self):
        for field, value in (("tasks", {}), ("context", []), ("requirements", None), ("interfaces", "I1")):
            self.bad("TYPE", lambda plan: plan.update({field: value}))
        self.bad("TYPE", lambda plan: plan["tasks"][0].update(functions=[None]))


class GraphAndScheduleTests(Base):
    def test_self_unknown_and_cycle_dependencies(self):
        self.bad("SELF_DEPENDENCY", lambda plan: plan["tasks"][0]["depends_on"].append("T1"))
        self.bad("UNKNOWN_DEPENDENCY", lambda plan: plan["tasks"][0]["depends_on"].append("T99"))
        self.bad("CYCLE", lambda plan: plan["tasks"][0]["depends_on"].append("T4"))

    def test_producer_registry_and_signature_consistency(self):
        self.bad("INTERFACE_PRODUCER", lambda plan: plan["interfaces"][0].update(producer="T99"))
        self.bad("INTERFACE_PRODUCER", lambda plan: plan["tasks"][0].update(produces=[]))
        self.bad("INTERFACE_PRODUCER", lambda plan: plan["tasks"][1]["produces"].append("I1"))
        self.bad("INTERFACE_SIGNATURE", lambda plan: plan["interfaces"][0].update(signature="def renamed(label: str) -> str"))
        self.bad("INTERFACE_SIGNATURE", lambda plan: plan["interfaces"][0].update(file="sample/encoding.py"))
        self.bad("INTERFACE_SIGNATURE", lambda plan: plan["tasks"][2]["consumes"][0].update(signature="def normalize_label(label:str)->str"))
        self.bad("INTERFACE_CONSUMER", lambda plan: plan["tasks"][2]["consumes"][0].update(interface="I99"))

    def test_consumers_need_real_transitive_dependencies(self):
        self.bad("INTERFACE_DEPENDENCY", lambda plan: plan["tasks"][2].update(depends_on=["T2"]))
        self.bad("INTERFACE_READ", lambda plan: plan["tasks"][2].update(files_read=[]))
        self.plan["tasks"][3]["consumes"].append({"interface": "I1", "signature": self.plan["interfaces"][0]["signature"]})
        self.plan["tasks"][3]["files_read"].append("sample/normalization.py")
        waveplan.validate_plan(self.plan)

    def test_capacity_and_stable_order(self):
        plan = self.independent()
        plan["max_parallel"] = 2
        self.assertEqual([["T1", "T2"], ["T3", "T4"]], [wave["tasks"] for wave in waveplan.schedule_plan(plan)["waves"]])
        plan["tasks"] = list(reversed(plan["tasks"]))
        self.assertEqual([["T4", "T3"], ["T2", "T1"]], [wave["tasks"] for wave in waveplan.schedule_plan(plan)["waves"]])

    def test_write_write_conflict_adds_wave_not_dependency(self):
        plan = self.independent()
        plan["tasks"][1]["files_allowed"].append("sample/normalization.py")
        before = deepcopy(plan)
        result = waveplan.schedule_plan(plan)
        self.assertEqual([["T1", "T3", "T4"], ["T2"]], [wave["tasks"] for wave in result["waves"]])
        self.assertEqual(1, result["depth_minimum"]["T2"])
        self.assertEqual(before, plan)

    def test_read_write_conflict_both_directions(self):
        for left, right in ((0, 1), (1, 0)):
            plan = self.independent()
            plan["tasks"][right]["files_read"].append(plan["tasks"][left]["files_allowed"][0])
            result = waveplan.schedule_plan(plan)
            locations = {tid: wave["wave"] for wave in result["waves"] for tid in wave["tasks"]}
            self.assertNotEqual(locations["T1"], locations["T2"])

    def test_read_read_is_parallel_and_resources_are_exclusive(self):
        plan = self.independent()
        for task in plan["tasks"]:
            task["files_read"] = ["shared/readme.txt"]
        self.assertEqual(["T1", "T2", "T3"], waveplan.schedule_plan(plan)["waves"][0]["tasks"])
        plan["tasks"][0]["resources"] = ["git-common:metadata"]
        plan["tasks"][1]["resources"] = ["git-common:metadata"]
        self.assertEqual(["T1", "T3", "T4"], waveplan.schedule_plan(plan)["waves"][0]["tasks"])

    def test_dependency_barrier_never_packs_producer_and_consumer(self):
        self.plan["max_parallel"] = 5
        result = waveplan.schedule_plan(self.plan)
        locations = {tid: wave["wave"] for wave in result["waves"] for tid in wave["tasks"]}
        for task in self.plan["tasks"]:
            for dependency in task["depends_on"]:
                self.assertLess(locations[dependency], locations[task["id"]])

    def test_large_chain_uses_iterative_graph_not_recursion(self):
        plan = self.independent()
        source = deepcopy(plan["tasks"][0])
        plan["tasks"] = []
        for number in range(150):
            task = deepcopy(source)
            task.update(id=f"T{number}", depends_on=[] if number == 0 else [f"T{number-1}"], files_allowed=[f"sample/f{number}.py"], requirement_ids=["R1", "R2", "R3", "R4"])
            task["functions"][0]["file"] = f"sample/f{number}.py"
            task["acceptance"] = [{"id": f"AC{number}", "text": "Check the exact assigned behavior."}]
            plan["tasks"].append(task)
        self.assertEqual(150, len(waveplan.schedule_plan(plan)["waves"]))


class PathTests(Base):
    def test_bad_portable_paths(self):
        invalid = ["/tmp/a", "C:/a", "C:a", "//server/share/a", "\\\\server\\share\\a", "a\\b", "a/../b", "../a", "./a", "a//b", "a/", "a/*", "a/?", "a/[x]", ".git/config", "src/.GIT/config", "a:stream", "a ", "a.", "a\nname", "NUL", "NUL.txt", "COM1.json", "LPT9", "COM¹.txt", "LPT³.txt", "x/<a>"]
        for path in invalid:
            with self.subTest(path=path), self.assertRaises(waveplan.PlanError):
                waveplan.validate_path(path)

    def test_good_portable_paths(self):
        for path in ("src/a.py", ".github/workflows/check.yml", "src/ação.py", "test data/file.txt", "COM10.txt"):
            self.assertEqual(path, waveplan.validate_path(path))
        self.assertEqual("src/", waveplan.validate_path("src/", directory=True))

    def test_case_and_unicode_aliases_are_rejected(self):
        self.bad("PATH_ALIAS", lambda plan: plan["tasks"][1]["files_read"].append("SAMPLE/normalization.py"))
        plan = self.independent()
        plan["tasks"][0]["files_read"] = ["src/café.py"]
        plan["tasks"][1]["files_read"] = ["src/cafe\u0301.py"]
        with self.assertRaises(waveplan.PlanError) as caught:
            waveplan.validate_plan(plan)
        self.assertEqual("PATH_ALIAS", caught.exception.code)

    def test_ancestor_file_and_directory_aliases(self):
        self.bad("PATH_ANCESTOR", lambda plan: plan["tasks"][0]["files_allowed"].append("sample"))
        self.bad("PATH_ANCESTOR", lambda plan: plan["tasks"][1]["files_forbidden"].append("sample/normalization.py/"))

    def test_forbidden_prefix_is_boundary_aware(self):
        self.assertTrue(waveplan.forbidden("src/a.py", ["src/"]))
        self.assertFalse(waveplan.forbidden("src2/a.py", ["src/"]))
        self.assertFalse(waveplan.forbidden("src/a.py", ["src/a"]))
        self.bad("SCOPE", lambda plan: plan["tasks"][0]["files_forbidden"].append("sample/"))


class InputAndDigestTests(Base):
    def load_payload(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "input.json"
            target.write_bytes(payload if isinstance(payload, bytes) else payload.encode("utf-8"))
            return waveplan.load_json(target)

    def test_duplicate_keys_and_nonfinite_are_rejected(self):
        for payload, code in (('{"x":1,"x":2}', "DUPLICATE_KEY"), ('{"nested":{"x":1,"x":2}}', "DUPLICATE_KEY"), ('{"x":NaN}', "NONFINITE"), ('{"x":Infinity}', "NONFINITE"), ('{"x":-Infinity}', "NONFINITE")):
            with self.subTest(payload=payload), self.assertRaises(waveplan.PlanError) as caught:
                self.load_payload(payload)
            self.assertEqual(code, caught.exception.code)

    def test_invalid_encoding_bom_and_json(self):
        for payload in (b"\xff", b"\xef\xbb\xbf{}", b"{", b'{"x":}'):
            with self.subTest(payload=payload), self.assertRaises(waveplan.PlanError) as caught:
                self.load_payload(payload)
            self.assertEqual("JSON", caught.exception.code)

    def test_limits_and_quoted_brackets(self):
        for payload in ("[" * 65 + "0" + "]" * 65, " " * (waveplan.MAX_INPUT_BYTES + 1)):
            with self.assertRaises(waveplan.PlanError) as caught:
                self.load_payload(payload)
            self.assertEqual("LIMIT", caught.exception.code)
        payload = {"data": "[" * 100 + '\\"' + "]" * 100}
        self.assertEqual(payload, self.load_payload(json.dumps(payload)))

    def test_input_directory_and_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.load_json(directory)
            self.assertEqual("INPUT_FILE", caught.exception.code)
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.load_json(Path(directory) / "absent.json")
            self.assertEqual("INPUT_IO", caught.exception.code)

    def test_changed_input_observation_is_rejected(self):
        original = (ROOT / "examples" / "plan.json").stat()
        changed = SimpleNamespace(st_mode=original.st_mode, st_dev=original.st_dev, st_ino=original.st_ino, st_size=original.st_size + 1, st_mtime_ns=original.st_mtime_ns)
        with patch.object(waveplan.Path, "stat", side_effect=[original, changed]):
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.load_json(ROOT / "examples" / "plan.json")
        self.assertEqual("CONCURRENT_INPUT", caught.exception.code)

    def test_canonical_utf8_hash_and_key_order(self):
        expected = hashlib.sha256(json.dumps(self.plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
        self.assertEqual(expected, waveplan.canonical_digest(self.plan))
        reverse = dict(reversed(list(self.plan.items())))
        self.assertEqual(expected, waveplan.canonical_digest(reverse))
        changed = deepcopy(self.plan)
        changed["goal"] += " More."
        self.assertNotEqual(expected, waveplan.canonical_digest(changed))

    def test_operations_do_not_mutate_inputs(self):
        before = deepcopy(self.plan)
        report = self.report()
        report_before = deepcopy(report)
        for operation in (waveplan.validate_plan, waveplan.schedule_plan, waveplan.render_plan):
            operation(self.plan)
        waveplan.brief_task(self.plan, "T3")
        waveplan.audit_report(self.plan, report)
        self.assertEqual(before, self.plan)
        self.assertEqual(report_before, report)
        self.assertEqual(waveplan.render_plan(self.plan), waveplan.render_plan(self.plan))


class ReportTests(Base):
    def test_done_is_not_verified_and_never_updates_state(self):
        result = waveplan.audit_report(self.plan, self.report())
        self.assertTrue(result["structurally_valid"])
        self.assertFalse(result["independently_verified"])
        self.assertFalse(result["state_updated"])
        self.assertIn("NÃO verificada", result["assurance"])

    def test_stale_digest_unknown_task_and_status(self):
        for field, value, code in (("plan_digest", "0" * 64, "STALE_PLAN"), ("task_id", "T99", "UNKNOWN_TASK"), ("status", "VERIFIED", "REPORT_STATUS")):
            report = self.report()
            report[field] = value
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.audit_report(self.plan, report)
            self.assertEqual(code, caught.exception.code)

    def test_done_requires_exact_green_exit_zero(self):
        for command, exit_code in (("different command", 0), (self.report()["verification"][0]["command"], 1)):
            report = self.report()
            report["verification"][0].update(command=command, exit_code=exit_code)
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.audit_report(self.plan, report)
            self.assertEqual("REPORT_GREEN", caught.exception.code)

    def test_acceptance_complete_no_extra_no_duplicate(self):
        for passed, code in (([], "REPORT_ACCEPTANCE"), (["AC99"], "REPORT_ACCEPTANCE"), (["AC1", "AC1"], "DUPLICATE")):
            report = self.report()
            report["acceptance_passed"] = passed
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.audit_report(self.plan, report)
            self.assertEqual(code, caught.exception.code)

    def test_scope_applies_even_to_blocked_reports(self):
        for status in ("DONE", "BLOCKED"):
            for file in ("package.json", "SAMPLE/normalization.py"):
                report = self.report(status)
                report["files_touched"] = [file]
                with self.assertRaises(waveplan.PlanError) as caught:
                    waveplan.audit_report(self.plan, report)
                self.assertEqual("REPORT_SCOPE", caught.exception.code)

    def test_blocked_can_omit_success_but_not_add_fields(self):
        report = self.report("BLOCKED")
        report.update(verification=[], acceptance_passed=[], notes=["A required dependency is unavailable."])
        self.assertEqual("BLOCKED", waveplan.audit_report(self.plan, report)["reported_status"])
        report["verified"] = True
        with self.assertRaises(waveplan.PlanError) as caught:
            waveplan.audit_report(self.plan, report)
        self.assertEqual("UNKNOWN_FIELD", caught.exception.code)

    def test_bool_exit_is_rejected(self):
        report = self.report()
        report["verification"][0]["exit_code"] = True
        with self.assertRaises(waveplan.PlanError) as caught:
            waveplan.audit_report(self.plan, report)
        self.assertEqual("RANGE", caught.exception.code)

    def test_same_command_red_then_green_is_legitimate_history(self):
        report = self.report()
        red = deepcopy(report["verification"][0])
        red.update(exit_code=1, summary="Worker claims expected RED failure.")
        report["verification"].insert(0, red)
        self.assertFalse(waveplan.audit_report(self.plan, report)["independently_verified"])

    def test_old_green_success_followed_by_failure_is_not_done(self):
        report = self.report()
        failed = deepcopy(report["verification"][0])
        failed.update(exit_code=1, summary="Worker reports later regression.")
        report["verification"].append(failed)
        with self.assertRaises(waveplan.PlanError) as caught:
            waveplan.audit_report(self.plan, report)
        self.assertEqual("REPORT_GREEN", caught.exception.code)


class CliAndRenderingTests(Base):
    def test_all_five_commands_and_json(self):
        with tempfile.TemporaryDirectory() as directory:
            report_file = Path(directory) / "report.json"
            report_file.write_text(json.dumps(self.report()), encoding="utf-8")
            source = str(ROOT / "examples" / "plan.json")
            for action, extras in (("validate", []), ("schedule", []), ("render", []), ("brief", ["T3"]), ("audit-report", [str(report_file)])):
                with self.subTest(action=action):
                    code, output, error = self.invoke([action, source, *extras, "--json"])
                    self.assertEqual(0, code)
                    self.assertEqual("", error)
                    self.assertTrue(json.loads(output)["ok"])
            self.assertEqual(["report.json"], [file.name for file in Path(directory).iterdir()])

    def test_json_global_flag_and_errors(self):
        source = str(ROOT / "examples" / "plan.json")
        self.assertTrue(json.loads(self.invoke(["--json", "validate", source])[1])["ok"])
        for args, code in ((["--json", "run"], 2), (["brief", source, "T99", "--json"], 1), (["validate", "missing.json", "--json"], 3)):
            result, output, error = self.invoke(args)
            self.assertEqual(code, result)
            self.assertEqual("", error)
            self.assertFalse(json.loads(output)["ok"])
        code, output, error = self.invoke(["run"])
        self.assertEqual(2, code)
        self.assertEqual("", output)
        self.assertIn("Solução", error)

    def test_help_and_stdout_default(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            waveplan.parser().parse_args(["--help"])
        self.assertEqual(0, caught.exception.code)
        self.assertIn("audit-report", out.getvalue())
        code, output, error = self.invoke(["schedule", str(ROOT / "examples" / "plan.json")])
        self.assertEqual(0, code)
        self.assertIn("Wave 1: T1, T2", output)
        self.assertEqual("", error)

    def test_brief_is_self_contained_without_unrelated_task_details(self):
        output = waveplan.brief_task(self.plan, "T3")
        for content in (waveplan.escape(self.plan["goal"]), waveplan.escape(self.plan["architecture"]), "Global anti-scope", "Locked decisions", "CONTAINS", "DOES NOT CONTAIN", "git add", "git commit", "ledger/state", "I1", "I2", "I3", "NOT proof"):
            self.assertIn(content, output)
        self.assertNotIn("### T4:", output)
        self.assertIn("NÃO verificada", output)

    def test_markdown_data_does_not_escape_its_blocks(self):
        self.plan["title"] = "<script>alert(1)</script> # [link](https://invalid.example)"
        command = "echo harmless\n```\n# injected heading\n````"
        self.plan["tasks"][0]["verification"]["green"]["command"] = command
        output = waveplan.render_plan(self.plan)
        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)
        self.assertIn("`````text\n" + command + "\n`````", output)

    def test_commands_are_never_executed_and_cli_never_writes_files(self):
        with tempfile.TemporaryDirectory() as directory:
            marker, source, report_file = (Path(directory) / name for name in ("executed.txt", "plan.json", "report.json"))
            opaque = f"python -c \"from pathlib import Path; Path({str(marker)!r}).write_text('executed')\""
            self.plan["tasks"][0]["verification"]["green"]["command"] = opaque
            self.plan["final_checks"][0]["command"] = opaque
            source.write_text(json.dumps(self.plan), encoding="utf-8")
            report_file.write_text(json.dumps(self.report()), encoding="utf-8")
            before = {file.name: file.read_bytes() for file in Path(directory).iterdir()}
            with patch("os.system", side_effect=AssertionError("shell execution forbidden")), patch("os.popen", side_effect=AssertionError("shell execution forbidden")):
                for action, extras in (("validate", []), ("schedule", []), ("render", []), ("brief", ["T1"]), ("audit-report", [str(report_file)])):
                    self.assertEqual(0, self.invoke([action, str(source), *extras, "--json"])[0])
            self.assertFalse(marker.exists())
            self.assertEqual(before, {file.name: file.read_bytes() for file in Path(directory).iterdir()})

    def test_helper_ast_is_stdlib_only_with_no_executor_or_network_import(self):
        source = (ROOT / "scripts" / "waveplan.py").read_text(encoding="utf-8")
        tree = ast.parse(source, feature_version=(3, 10))
        prohibited = {"subprocess", "socket", "urllib", "http", "requests", "openai", "ctypes", "multiprocessing", "pty"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], prohibited)
                    self.assertIn(alias.name.split(".")[0], sys_stdlib_names())
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module.split(".")[0], prohibited)
                self.assertIn(node.module.split(".")[0], sys_stdlib_names())
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"exec", "eval", "compile", "__import__"})
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, {"system", "popen", "spawn", "run", "Popen", "write_text", "write_bytes", "unlink", "mkdir", "rename"})


def sys_stdlib_names():
    import sys
    return sys.stdlib_module_names


class RepositoryTests(Base):
    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest("Symlink creation unavailable: " + str(error))

    def test_empty_repository_checks_do_not_create_files(self):
        with tempfile.TemporaryDirectory() as directory:
            waveplan.validate_plan(self.plan, directory)
            self.assertEqual([], list(Path(directory).iterdir()))

    def test_symlink_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root, outside = Path(directory) / "repo", Path(directory) / "outside"
            root.mkdir()
            outside.mkdir()
            self.symlink(root / "sample", outside, True)
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.validate_plan(self.plan, root)
            self.assertEqual("PATH_ESCAPE", caught.exception.code)

    def test_symlink_into_git_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            (root / "sample").mkdir()
            (root / ".git" / "config").write_text("fixture", encoding="utf-8")
            self.symlink(root / "sample" / "normalization.py", root / ".git" / "config")
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.validate_plan(self.plan, root)
            self.assertEqual("PATH_ADMIN", caught.exception.code)


    def test_inside_symlink_aliases_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample").mkdir()
            original = root / "sample" / "normalization.py"
            original.write_text("fixture", encoding="utf-8")
            self.symlink(root / "sample" / "alias.py", original)
            self.plan["tasks"][0]["files_read"].append("sample/alias.py")
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.validate_plan(self.plan, root)
            self.assertEqual("REPOSITORY_ALIAS", caught.exception.code)

    def test_existing_hardlink_aliases_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample").mkdir()
            original = root / "sample" / "normalization.py"
            original.write_text("fixture", encoding="utf-8")
            try:
                os.link(original, root / "sample" / "alias.py")
            except (OSError, NotImplementedError) as error:
                self.skipTest("Hard links unavailable: " + str(error))
            if not original.stat().st_ino:
                self.skipTest("Filesystem does not expose stable file identities.")
            self.plan["tasks"][0]["files_read"].append("sample/alias.py")
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.validate_plan(self.plan, root)
            self.assertEqual("REPOSITORY_ALIAS", caught.exception.code)

    def test_wrong_existing_file_kind_and_non_directory_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample").mkdir()
            (root / "sample" / "normalization.py").mkdir()
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.validate_plan(self.plan, root)
            self.assertEqual("REPOSITORY_TYPE", caught.exception.code)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample").write_text("not a directory", encoding="utf-8")
            with self.assertRaises(waveplan.PlanError) as caught:
                waveplan.validate_plan(self.plan, root)
            self.assertIn(caught.exception.code, {"REPOSITORY_TYPE", "REPOSITORY_IO"})

    def test_repository_cli_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, error = self.invoke(["validate", str(ROOT / "examples" / "plan.json"), "--repository", directory, "--json"])
            self.assertEqual(0, code)
            self.assertTrue(json.loads(output)["ok"])
            self.assertEqual("", error)


class SchemaContractTests(Base):
    def test_schema_is_local_and_agrees_with_closed_contract_fields(self):
        schema = waveplan.load_json(ROOT / "assets" / "plan.schema.json")
        self.assertEqual(set(schema["required"]), waveplan.PLAN_FIELDS)
        self.assertEqual(set(schema["properties"]), waveplan.PLAN_FIELDS)
        self.assertEqual(set(schema["$defs"]["task"]["required"]), waveplan.TASK_FIELDS)
        self.assertEqual(set(schema["$defs"]["task"]["properties"]), waveplan.TASK_FIELDS)
        self.assertEqual(1, schema["$defs"]["task"]["properties"]["functions"]["minItems"])
        def references(value):
            if isinstance(value, dict):
                if "$ref" in value:
                    reference = value["$ref"]
                    self.assertTrue(reference.startswith("#/$defs/"))
                    self.assertIn(reference.removeprefix("#/$defs/"), schema["$defs"])
                for entry in value.values():
                    references(entry)
            elif isinstance(value, list):
                for entry in value:
                    references(entry)
        references(schema)

    def test_directory_spelling_aliases_are_rejected_even_for_different_files(self):
        self.bad("PATH_ALIAS", lambda plan: plan["tasks"][1]["files_read"].append("SAMPLE/other.py"))


if __name__ == "__main__":
    unittest.main()
