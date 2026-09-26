#!/usr/bin/env python3
"""Validate the DRAFT baseline artifacts and their immutable delivery metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAG = "draft-contract-v1"
RAW_PREFIX = f"https://raw.githubusercontent.com/smwy-cj/DevOps-Pro/{TAG}/"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"FAIL {message}")


def check_artifact(name: str, artifact: dict, local_path: Path, failures: list[str]) -> None:
    uri = artifact.get("uri", "")
    if not uri.startswith(RAW_PREFIX):
        fail(f"{name}: URI is not on immutable anonymous Raw tag", failures)
    if artifact.get("authentication") != "NONE":
        fail(f"{name}: authentication is not NONE", failures)
    try:
        data = local_path.read_bytes()
    except OSError as exc:
        fail(f"{name}: cannot read local artifact: {exc}", failures)
        return
    actual_hash = sha256(data)
    actual_size = len(data)
    if actual_hash != artifact.get("sha256") or actual_size != artifact.get("size_bytes"):
        fail(f"{name}: local SHA-256/size mismatch", failures)
    else:
        print(f"PASS {name}: {actual_hash} / {actual_size} bytes")


def check_utf8(name: str, path: Path, failures: list[str]) -> None:
    try:
        path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fail(f"{name}: not valid UTF-8", failures)
    else:
        print(f"PASS {name}: UTF-8")


def check_remote(artifacts: list[tuple[str, dict]], failures: list[str]) -> None:
    for name, artifact in artifacts:
        try:
            with urllib.request.urlopen(artifact["uri"], timeout=20) as response:
                data = response.read()
                status = response.status
        except Exception as exc:  # noqa: BLE001
            fail(f"{name}: anonymous GET failed: {exc}", failures)
            continue
        if status != 200 or sha256(data) != artifact.get("sha256") or len(data) != artifact.get("size_bytes"):
            fail(f"{name}: remote status/SHA-256/size mismatch", failures)
        else:
            print(f"PASS {name}: anonymous GET")


def check_image(success: dict, failures: list[str]) -> None:
    image = success["output"]["image"]
    image_ref = os.environ.get("DRAFT_IMAGE_REF")
    if not image_ref:
        fail("image: DRAFT_IMAGE_REF is not configured for anonymous pull", failures)
        return
    expected = image["digest"]
    if not image_ref.endswith("@" + expected):
        fail("image: DRAFT_IMAGE_REF digest does not match contract", failures)
        return
    result = subprocess.run(["docker", "pull", image_ref], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        fail(f"image: anonymous docker pull failed: {result.stderr.strip()}", failures)
    else:
        print(f"PASS image: anonymous docker pull {image_ref}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-remote", action="store_true")
    parser.add_argument("--check-image", action="store_true")
    args = parser.parse_args()
    failures: list[str] = []
    request = load_json(ROOT / "contracts/draft-request.json")
    success = load_json(ROOT / "contracts/draft-success.json")
    failure = load_json(ROOT / "contracts/draft-failure.json")

    if request["input"]["expected_output"] != success["output"]["actual_output"]:
        fail("request and success output disagree", failures)
    if success["output"]["build_exit_code"] != 0 or success["output"]["verify_exit_code"] != 0:
        fail("success result contains a non-zero exit code", failures)
    if failure["error"]["code"] != "COMMAND_NOT_FOUND" or failure["error"]["exit_code"] != 127:
        fail("failure result does not describe the expected missing make command", failures)

    artifact_root = ROOT / "draft-baseline"
    artifacts = [
        ("failure Dockerfile", failure["output"]["dockerfile"], artifact_root / "Dockerfile.broken"),
        ("failure build log", failure["output"]["build_log"], artifact_root / "artifacts/build-failed.log"),
        ("success Dockerfile", success["output"]["dockerfile"], artifact_root / "Dockerfile.reference"),
        ("success build log", success["output"]["build_log"], artifact_root / "artifacts/build-success.log"),
        ("run log", success["output"]["run_log"], artifact_root / "artifacts/run-result.log"),
        ("image digest file", success["output"]["image"]["digest_artifact"], artifact_root / "artifacts/image-id.txt"),
    ]
    for name, artifact, path in artifacts:
        check_artifact(name, artifact, path, failures)
    for name, _, path in artifacts:
        if path.suffix == ".log":
            check_utf8(name, path, failures)

    image_digest = success["output"]["image"]["digest"]
    recorded_digest = (artifact_root / "artifacts/image-id.txt").read_text(encoding="utf-8").strip()
    if recorded_digest != image_digest or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_digest):
        fail("image digest does not match image-id.txt or digest format", failures)
    else:
        print("PASS image digest: image-id.txt matches success result")

    if args.check_image:
        check_image(success, failures)
    if not args.skip_remote:
        check_remote([(name, artifact) for name, artifact, _ in artifacts], failures)

    print(f"{len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
