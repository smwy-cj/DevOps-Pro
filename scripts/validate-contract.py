#!/usr/bin/env python3
"""Validate the A06/B06 E2 DRAFT and REPAIR examples."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "contracts/examples/repair"
ARTIFACTS = ROOT / "contracts/artifacts/a06-b06"
DRAFT_ROOT = ROOT / "draft-baseline"
SCHEMA = ROOT / "contracts/schemas/task.schema.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def semantic_code(request: dict) -> str:
    data = request["input"]
    if data["finding"]["type"] != "MISSING":
        return "REPAIR_7001"
    commit = data["repository"]["commit"]
    if commit != data["error_report"]["artifact"]["repository_commit"] or commit != data["finding"]["commit"]:
        return "REPAIR_7002"
    configuration_id = data["configuration"]["configuration_id"]
    if configuration_id != data["error_report"]["artifact"]["configuration_id"] or configuration_id != data["finding"]["configuration_id"]:
        return "REPAIR_7003"
    if data["error_report"]["artifact"]["uri"] != data["error_report"]["read_method"]["url"]:
        return "REPAIR_7004"
    path = data["makefile_path"]
    if path.startswith(("/", "\\")) or re.search(r"(^|[/\\])\.\.([/\\]|$)", path):
        return "REQUEST_1001"
    return "OK"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-remote", action="store_true", help="Skip A06 HTTP report check")
    args = parser.parse_args()
    checks: list[tuple[str, bool]] = []

    def check(name: str, passed: bool) -> None:
        checks.append((name, passed))
        print(("PASS" if passed else "FAIL") + " " + name)

    schema = read_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_cases = [
        (ROOT / "contracts/draft-request.json", True),
        (ROOT / "contracts/draft-success.json", True),
        (ROOT / "contracts/draft-failure.json", True),
        (EXAMPLES / "repair-request.json", True),
        (EXAMPLES / "repair-result-success.json", True),
        (EXAMPLES / "repair-response-reject-redundant.json", True),
        (EXAMPLES / "repair-response-reject-commit-mismatch.json", True),
        (EXAMPLES / "repair-response-reject-configuration-mismatch.json", True),
        (ARTIFACTS / "repair-report.json", True),
        (EXAMPLES / "repair-request-reject-redundant.json", False),
        (EXAMPLES / "repair-request-reject-commit-mismatch.json", True),
        (EXAMPLES / "repair-request-reject-configuration-mismatch.json", True),
    ]
    for path, expected_valid in schema_cases:
        actual_valid = validator.is_valid(read_json(path))
        check("schema " + path.name, actual_valid == expected_valid)

    semantic_cases = [
        ("repair-request.json", "OK"),
        ("repair-request-reject-redundant.json", "REPAIR_7001"),
        ("repair-request-reject-commit-mismatch.json", "REPAIR_7002"),
        ("repair-request-reject-configuration-mismatch.json", "REPAIR_7003"),
    ]
    for filename, expected in semantic_cases:
        check("semantic " + filename, semantic_code(read_json(EXAMPLES / filename)) == expected)

    for kind in ("redundant", "commit-mismatch", "configuration-mismatch"):
        filename = "repair-response-reject-" + kind + ".json"
        expected = {"redundant": "REPAIR_7001", "commit-mismatch": "REPAIR_7002", "configuration-mismatch": "REPAIR_7003"}[kind]
        check("response " + kind, read_json(EXAMPLES / filename)["error"]["code"] == expected)

    success = read_json(EXAMPLES / "repair-result-success.json")
    report = read_json(ARTIFACTS / "repair-report.json")
    artifact_cases = [
        ("fix-main-o-config-h.patch", success["output"]["patch"]),
        ("repair-report.json", success["output"]["repair_report"]),
        ("repair-verification.txt", report["verification"]["log"]),
    ]
    for filename, metadata in artifact_cases:
        data = (ARTIFACTS / filename).read_bytes()
        check("artifact " + filename, sha256(data) == metadata["sha256"] and len(data) == metadata["size_bytes"])

    check(
        "result/report consistency",
        success["output"]["provenance"] == report["provenance"]
        and success["output"]["verification"]["recheck"] == report["verification"]["recheck"]
        and success["output"]["repair_report"]["repository_commit"] == report["repository_commit"]
        and success["output"]["repair_report"]["configuration_id"] == report["configuration_id"],
    )

    draft_request = read_json(ROOT / "contracts/draft-request.json")
    draft_success = read_json(ROOT / "contracts/draft-success.json")
    draft_failure = read_json(ROOT / "contracts/draft-failure.json")
    draft_output = draft_success["output"]
    check(
        "DRAFT request/result consistency",
        draft_success["input"] == draft_request["input"]
        and draft_output["repository_commit"] == draft_request["input"]["repository"]["commit"]
        and draft_output["configuration"] == draft_request["input"]["configuration"]
        and draft_output["verification"]["actual_output"] == draft_request["input"]["expected_output"]
        and draft_failure["input"] == draft_request["input"]
        and draft_failure["error"]["code"] == "ENV_3002",
    )

    image = draft_output["image"]
    check(
        "DRAFT immutable image reference",
        image["reference"].endswith("@" + image["digest"])
        and image["pull_command"] == ["docker", "pull", image["reference"]],
    )

    draft_artifacts = [
        (DRAFT_ROOT / "Dockerfile.reference", draft_output["dockerfile"]),
        (DRAFT_ROOT / "artifacts/build-success.log", draft_output["build_log"]),
        (DRAFT_ROOT / "artifacts/run-result.log", draft_output["run_log"]),
        (DRAFT_ROOT / "Dockerfile.broken", draft_failure["output"]["dockerfile"]),
        (DRAFT_ROOT / "artifacts/build-failed.log", draft_failure["output"]["build_log"]),
    ]
    for path, metadata in draft_artifacts:
        data = path.read_bytes()
        try:
            data.decode("utf-8")
            valid_utf8 = True
        except UnicodeDecodeError:
            valid_utf8 = False
        check(
            "DRAFT artifact " + path.name,
            valid_utf8
            and metadata["encoding"] == "utf-8"
            and metadata["uri"] == metadata["read_method"]["url"]
            and sha256(data) == metadata["sha256"]
            and len(data) == metadata["size_bytes"],
        )

    if not args.skip_remote:
        reference = read_json(EXAMPLES / "repair-request.json")["input"]["error_report"]
        with tempfile.TemporaryDirectory(prefix="e2-repair-check-") as temporary:
            body = Path(temporary) / "report.json"
            headers = Path(temporary) / "headers.txt"
            response = subprocess.run(
                ["curl", "-L", "--fail", "--silent", "--show-error", "--max-time", "20", "-D", str(headers), "-o", str(body), "-w", "%{http_code}", reference["read_method"]["url"]],
                capture_output=True,
                text=True,
                check=False,
            )
            content_type = next(
                (line.split(":", 1)[1].strip().lower() for line in reversed(headers.read_text().splitlines()) if line.lower().startswith("content-type:")),
                "",
            ) if headers.exists() else ""
            data = body.read_bytes() if body.exists() else b""
            remote_ok = (
                response.returncode == 0
                and response.stdout.strip() == "200"
                and content_type.startswith("text/plain")
                and sha256(data) == reference["artifact"]["sha256"]
                and len(data) == reference["artifact"]["size_bytes"]
            )
            if remote_ok:
                remote_report = json.loads(data.decode("utf-8"))
                request = read_json(EXAMPLES / "repair-request.json")
                remote_ok = (
                    remote_report["repository"] == request["input"]["repository"]
                    and remote_report["configuration"] == request["input"]["configuration"]
                    and all(request["input"]["finding"][key] == remote_report["findings"][0][key] for key in request["input"]["finding"])
                )
            check("remote A06 report", remote_ok)

        for path, metadata in draft_artifacts:
            with tempfile.TemporaryDirectory(prefix="e2-draft-artifact-") as temporary:
                body = Path(temporary) / path.name
                headers = Path(temporary) / "headers.txt"
                response = subprocess.run(
                    ["curl", "-L", "--fail", "--silent", "--show-error", "--max-time", "20", "-D", str(headers), "-o", str(body), "-w", "%{http_code}", metadata["uri"]],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                data = body.read_bytes() if body.exists() else b""
                content_type = next(
                    (line.split(":", 1)[1].strip().lower() for line in reversed(headers.read_text().splitlines()) if line.lower().startswith("content-type:")),
                    "",
                ) if headers.exists() else ""
                check(
                    "remote DRAFT artifact " + path.name,
                    response.returncode == 0
                    and response.stdout.strip() == "200"
                    and content_type.startswith("text/plain")
                    and sha256(data) == metadata["sha256"]
                    and len(data) == metadata["size_bytes"],
                )

        manifest_ok = False
        if shutil.which("docker"):
            manifest = subprocess.run(
                ["docker", "manifest", "inspect", "--verbose", image["reference"]],
                capture_output=True,
                text=True,
                check=False,
            )
            if manifest.returncode == 0:
                manifest_data = json.loads(manifest.stdout)
                descriptor = manifest_data.get("Descriptor", {})
                platform = descriptor.get("platform", {})
                manifest_ok = (
                    descriptor.get("digest") == image["digest"]
                    and descriptor.get("mediaType") == image["media_type"]
                    and platform.get("os") == "linux"
                    and platform.get("architecture") == "amd64"
                )
        check("remote DRAFT image manifest", manifest_ok)

    passed = sum(result for _, result in checks)
    print(f"{passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
