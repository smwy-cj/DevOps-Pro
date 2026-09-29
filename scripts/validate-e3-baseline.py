#!/usr/bin/env python3
"""Validate the committed E3 baseline metadata and evidence."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
E3_ROOT = REPOSITORY_ROOT / "e3-baseline"
FIXED_SOURCE_COMMIT = "be73686c6a9fdbb7c4d3eadb45779233afa33083"
STYLE_NAMES = ("target", "macro", "implicit", "hybrid")
STYLE_REQUIRED_FILES = {
    "Makefile",
    "Makefile.before",
    "Makefile.expected",
    "config.h",
    "main.c",
    "patch-check.txt",
    "reason.md",
    "reference.patch",
    "verification.log",
}


class Validation:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.check_count = 0

    def check(self, condition: bool, message: str) -> None:
        self.check_count += 1
        if condition:
            print(f"PASS: {message}")
        else:
            print(f"FAIL: {message}")
            self.failures.append(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def read_json(path: Path, validation: Validation) -> dict[str, Any]:
    try:
        value = json.loads(read_text(path))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        validation.check(False, f"JSON is parseable: {path.relative_to(REPOSITORY_ROOT)} ({error})")
        return {}

    validation.check(isinstance(value, dict), f"JSON is parseable: {path.relative_to(REPOSITORY_ROOT)}")
    return value if isinstance(value, dict) else {}


def has_labeled_value(log_text: str, label: str, value: str) -> bool:
    pattern = rf"(?m)^{re.escape(label)}:\s*\n{re.escape(value)}\s*$"
    return re.search(pattern, log_text) is not None


def validate_source_metadata(validation: Validation) -> None:
    expected = read_json(E3_ROOT / "draft" / "expected-result.json", validation)
    missing = read_json(
        E3_ROOT / "mdfixer" / "fixed-input" / "missing-report.json", validation
    )
    commands = read_json(E3_ROOT / "commands.json", validation)
    observations = read_json(E3_ROOT / "observations.json", validation)

    validation.check(
        expected.get("repository_commit") == FIXED_SOURCE_COMMIT,
        "draft expected result references the fixed source commit",
    )
    validation.check(
        missing.get("repository", {}).get("commit") == FIXED_SOURCE_COMMIT,
        "MDFixer missing report references the fixed source commit",
    )
    validation.check(
        commands.get("source_commit") == FIXED_SOURCE_COMMIT,
        "commands metadata references the fixed source commit",
    )
    validation.check(
        observations.get("source_commit") == FIXED_SOURCE_COMMIT,
        "observations metadata references the fixed source commit",
    )

    command_styles = commands.get("mdfixer", {}).get("styles", {})
    for style in STYLE_NAMES:
        entry = command_styles.get(style, {})
        validation.check(
            all(key in entry for key in ("build", "verify", "patch", "restore")),
            f"commands metadata records build, verify, patch, and restore for {style}",
        )


def validate_repair_styles(validation: Validation) -> None:
    styles_root = E3_ROOT / "mdfixer" / "styles"
    for style in STYLE_NAMES:
        style_root = styles_root / style
        missing_files = sorted(
            filename
            for filename in STYLE_REQUIRED_FILES
            if not (style_root / filename).is_file()
        )
        if style == "implicit" and not (style_root / "dependency-file.txt").is_file():
            missing_files.append("dependency-file.txt")

        validation.check(
            not missing_files,
            f"{style} repair style has all required files"
            + (f" (missing: {', '.join(missing_files)})" if missing_files else ""),
        )

        if missing_files:
            continue

        validation.check(
            read_text(style_root / "Makefile")
            == read_text(style_root / "Makefile.expected"),
            f"{style} Makefile matches the expected repaired file",
        )

        verification_log = read_text(style_root / "verification.log")
        validation.check(
            has_labeled_value(verification_log, "initial_output", "1"),
            f"{style} verification log contains initial value 1",
        )
        validation.check(
            has_labeled_value(
                verification_log, "output_after_config_change", "3"
            ),
            f"{style} verification log contains repaired value 3",
        )

    dependency_text = read_text(styles_root / "implicit" / "dependency-file.txt")
    validation.check(
        "config.h" in dependency_text,
        "implicit dependency file contains config.h",
    )


def validate_invalid_candidate(validation: Validation) -> None:
    invalid_root = E3_ROOT / "mdfixer" / "invalid-candidate"
    rejection = read_json(invalid_root / "rejection.json", validation)
    recovery = rejection.get("recovery", {})

    validation.check(
        rejection.get("source_commit") == FIXED_SOURCE_COMMIT,
        "invalid candidate references the fixed source commit",
    )
    validation.check(
        rejection.get("decision") == "REJECTED",
        "invalid candidate decision is REJECTED",
    )
    validation.check(
        recovery.get("build_exit_code") == 0
        and recovery.get("run_exit_code") == 0
        and recovery.get("stdout_exact") == "1\n",
        "invalid candidate recovery metadata records a successful build and run",
    )
    validation.check(
        read_text(invalid_root / "Makefile")
        == read_text(invalid_root / "Makefile.before"),
        "invalid candidate Makefile was restored",
    )

    restore_codes = read_text(invalid_root / "restore-exit-codes.txt")
    validation.check(
        "restore_build_exit_code=0" in restore_codes
        and "restore_run_exit_code=0" in restore_codes,
        "invalid candidate restore exit codes are zero",
    )
    validation.check(
        read_text(invalid_root / "restore.log").strip().endswith("1"),
        "invalid candidate restore log records output 1",
    )
    validation.check(
        "nonexistent.h" in read_text(invalid_root / "failed-validation.log"),
        "invalid candidate failure log records the nonexistent dependency",
    )


def validate_draft(validation: Validation) -> None:
    logs_root = E3_ROOT / "draft" / "logs"
    exit_codes = read_text(logs_root / "host-exit-codes.txt")
    host_output = read_text(logs_root / "host-run.log")

    validation.check(
        "build_exit_code=0" in exit_codes and "run_exit_code=0" in exit_codes,
        "DRAFT host build and run exit codes are zero",
    )
    validation.check(
        host_output.strip() == "hello E3",
        "DRAFT host log outputs hello E3",
    )


def main() -> int:
    validation = Validation()
    validate_source_metadata(validation)
    validate_repair_styles(validation)
    validate_invalid_candidate(validation)
    validate_draft(validation)

    print()
    if validation.failures:
        print(
            f"RESULT: FAILED ({len(validation.failures)} of "
            f"{validation.check_count} checks failed)"
        )
        return 1

    print(f"RESULT: PASSED ({validation.check_count} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
