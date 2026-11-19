"""Regression coverage for B06's E13 report, registry and scanner fixes."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pipeline = load_module("b06_pipeline", "labs/e11e12/pipeline.py")
scanner = load_module(
    "b06_secret_scan", "labs/e11e12/environment/scripts/secret_scan.py"
)
from draft import autobuild


class FixedReportTests(unittest.TestCase):
    def run_report(self, hash_mode):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            candidate = root / "candidate.Dockerfile"
            candidate.write_text("candidate input\n")
            fixed = root / "fixed.json"
            target = "1" * 40
            envelope = {
                "schema_version": "e11e12-1",
                "kind": "fixed-md",
                "status": "SUCCEEDED",
                "commit": target,
                "data": {"commit": target, "findings": []},
            }
            original = json.dumps(envelope).encode()
            fixed.write_bytes(original)
            request = {
                "mode": "e11-b",
                "repo": str(repo),
                "base": "0" * 40,
                "target": target,
                "candidate": str(candidate),
                "fixed_report": str(fixed),
            }
            if hash_mode != "absent":
                request["fixed_report_sha256"] = hashlib.sha256(original).hexdigest()
            if hash_mode == "tampered":
                fixed.write_bytes(original + b"\n")

            def fake_snapshot(repo, revision, destination, *args):
                destination.mkdir(parents=True)
                (destination / "Makefile").write_text("main.o: main.c\n")
                return revision

            def fake_build(project, candidate, output, expected, timeout):
                output.mkdir(parents=True)
                report = {"status": "SUCCEEDED"}
                (output / "result.json").write_text(json.dumps(report))
                return report

            with mock.patch.object(
                pipeline, "snapshot", side_effect=fake_snapshot,
            ), mock.patch.object(
                autobuild, "auto_build", side_effect=fake_build,
            ), mock.patch.object(
                pipeline, "patch", side_effect=ValueError("TEST_REACHED_PATCH"),
            ) as patcher:
                result = pipeline.execute(request, root / "out")
                self.assertEqual(result["status"], "FAILED")
                if hash_mode == "tampered":
                    self.assertEqual(result["error"]["code"], "ARTIFACT_HASH_MISMATCH")
                    patcher.assert_not_called()
                else:
                    self.assertEqual(result["error"]["message"], "TEST_REACHED_PATCH")
                    patcher.assert_called_once()
            self.assertEqual(fixed.read_bytes(), original + (
                b"\n" if hash_mode == "tampered" else b""
            ))

    def test_execute_rejects_changed_fixed_report_before_patch(self):
        self.run_report("tampered")

    def test_execute_accepts_matching_report_hash(self):
        self.run_report("matching")

    def test_execute_supports_request_without_report_hash(self):
        self.run_report("absent")


class SecretScannerTests(unittest.TestCase):
    def test_unquoted_json_reads_are_not_literal_credentials(self):
        assignment = "tok" + "en = "
        for expression in (
            assignment + 'json.load(response)["token"]',
            "+" + assignment + 'json.loads(response)["token"]',
        ):
            with self.subTest(expression=expression):
                self.assertEqual(scanner.scan_text(expression, "test"), [])

    def test_quoted_json_expressions_are_still_detected(self):
        assignment = "tok" + "en = "
        for expression in (
            assignment + '"json.load(response)"',
            assignment + "'json.loads(response)'",
        ):
            with self.subTest(expression=expression):
                self.assertTrue(scanner.scan_text(expression, "test"))

    def test_literals_and_keys_inside_json_are_still_detected(self):
        fake_key = "sk-" + "b" * 25
        assignment = "tok" + "en = "
        cases = (
            assignment + '"' + "a" * 32 + '"',
            'key = "' + fake_key + '"',
            assignment + "json.loads('" + json.dumps({"api_key": fake_key}) + "')",
        )
        for expression in cases:
            with self.subTest(expression=expression):
                self.assertTrue(scanner.scan_text(expression, "test"))


class DraftMirrorTests(unittest.TestCase):
    def run_build(self, image):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            broken = f"FROM {image}\nWORKDIR /work\nRUN make app\nCMD [\"./app\"]\n"
            (project / "Dockerfile.broken").write_text(broken)
            pinned = image + "@sha256:" + "a" * 64
            candidate = root / "candidate.Dockerfile"
            candidate_text = broken.replace(
                f"FROM {image}", f"FROM {pinned}"
            ).replace("RUN make app", "RUN install-build-tools\nRUN make app")
            candidate.write_text(candidate_text)
            commands = []

            def fake_execute(argv, stdout, stderr, timeout):
                Path(stdout).write_text("")
                Path(stderr).write_text("")
                if argv[:2] == ["docker", "build"]:
                    commands.append(argv)
                    if "iter-01" in argv[argv.index("-f") + 1]:
                        Path(stderr).write_text("/bin/sh: 1: make: not found\n")
                        return 1
                elif argv[:3] == ["docker", "image", "inspect"]:
                    Path(stdout).write_text(json.dumps([{"Id": "sha256:" + "b" * 64}]))
                elif argv[:2] == ["docker", "run"]:
                    Path(stdout).write_text("1\n")
                else:
                    self.fail(f"Unexpected Docker command: {argv}")
                return 0

            out = root / "evidence"
            with mock.patch.object(autobuild, "execute", side_effect=fake_execute):
                result = autobuild.auto_build(project, candidate, out, "1")
            self.assertEqual(result["status"], "SUCCEEDED", result.get("error"))
            self.assertEqual(candidate.read_text(), candidate_text)
            self.assertEqual((project / "Dockerfile.broken").read_text(), broken)
            self.assertEqual(len(commands), 2)
            for number, command in enumerate(commands, 1):
                dockerfile = (out / f"iter-{number:02d}" / "Dockerfile").read_text()
                self.assertEqual(dockerfile.splitlines()[0], "FROM " + pinned)
                self.assertEqual(command, result["attempts"][number - 1]["command"])
                if image == "python:3.13-slim":
                    self.assertIn("--build-context", command)
                    value = command[command.index("--build-context") + 1]
                    self.assertEqual(
                        value, pinned + "=docker-image://m.daocloud.io/docker.io/library/" + pinned
                    )
                else:
                    self.assertNotIn("--build-context", command)

    def test_both_builds_record_mirror_with_the_original_digest(self):
        self.run_build("python:3.13-slim")

    def test_other_base_images_keep_their_build_command(self):
        self.run_build("alpine:3.23")


if __name__ == "__main__":
    unittest.main()
