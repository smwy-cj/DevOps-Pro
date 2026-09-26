#!/usr/bin/env python3
"""Download and verify every blob of the public DRAFT image without credentials."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_REFERENCE = "ghcr.io/smwy-cj/devops-pro/draft-reference@sha256:b2dbfef36913f7322287f155650cea3f064d2986d414700e916f87404402d2c7"
MANIFEST_MEDIA_TYPE = "application/vnd.docker.distribution.manifest.v2+json"


def request(url: str, token: str | None = None, accept: str | None = None):
    headers = {"User-Agent": "B06-E2-DRAFT-validator"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if accept:
        headers["Accept"] = accept
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60)


def parse_reference(reference: str) -> tuple[str, str, str]:
    registry, remainder = reference.split("/", 1)
    repository, digest = remainder.rsplit("@", 1)
    if registry != "ghcr.io" or not digest.startswith("sha256:"):
        raise ValueError("expected a ghcr.io reference fixed to sha256")
    return registry, repository, digest


def download_blob(url: str, token: str, expected_digest: str, expected_size: int, destination: Path) -> None:
    hasher = hashlib.sha256()
    size = 0
    with request(url, token=token) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            hasher.update(chunk)
            size += len(chunk)
    actual_digest = "sha256:" + hasher.hexdigest()
    if actual_digest != expected_digest or size != expected_size:
        raise RuntimeError(
            f"blob mismatch: expected {expected_digest}/{expected_size}, got {actual_digest}/{size}"
        )
    print(f"PASS blob {expected_digest} {size} bytes")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", default=DEFAULT_REFERENCE)
    args = parser.parse_args()
    _, repository, digest = parse_reference(args.reference)

    token_url = "https://ghcr.io/token?" + urllib.parse.urlencode(
        {"service": "ghcr.io", "scope": f"repository:{repository}:pull"}
    )
    with request(token_url) as response:
        token = json.load(response)["token"]
    print("PASS anonymous bearer token")

    manifest_url = f"https://ghcr.io/v2/{repository}/manifests/{digest}"
    with request(manifest_url, token=token, accept=MANIFEST_MEDIA_TYPE) as response:
        manifest_bytes = response.read()
        response_digest = response.headers.get("Docker-Content-Digest")
        response_media_type = response.headers.get_content_type()
    actual_manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    if response_digest != digest or actual_manifest_digest != digest:
        raise RuntimeError(
            f"manifest digest mismatch: requested={digest} header={response_digest} actual={actual_manifest_digest}"
        )
    if response_media_type != MANIFEST_MEDIA_TYPE:
        raise RuntimeError(f"unexpected manifest media type: {response_media_type}")
    manifest = json.loads(manifest_bytes)
    print(f"PASS manifest {digest} {len(manifest_bytes)} bytes")

    descriptors = [manifest["config"], *manifest["layers"]]
    total = 0
    with tempfile.TemporaryDirectory(prefix="b06-draft-image-") as temporary:
        temporary_path = Path(temporary)
        for index, descriptor in enumerate(descriptors):
            blob_url = f"https://ghcr.io/v2/{repository}/blobs/{descriptor['digest']}"
            download_blob(
                blob_url,
                token,
                descriptor["digest"],
                descriptor["size"],
                temporary_path / f"blob-{index}",
            )
            total += descriptor["size"]

        config_path = temporary_path / "blob-0"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("os") != "linux" or config.get("architecture") != "amd64":
            raise RuntimeError(f"unexpected image platform: {config.get('os')}/{config.get('architecture')}")
    print(f"PASS platform linux/amd64")
    print(f"PASS anonymous image pull {len(descriptors)} blobs {total} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
