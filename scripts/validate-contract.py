#!/usr/bin/env python3
"""Validate the A06/B06 E2 REPAIR examples (requires jsonschema 4.x)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "contracts/examples/repair"
ARTIFACTS = ROOT / "contracts/artifacts/a06-b06"
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

    passed = sum(result for _, result in checks)
    print(f"{passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
