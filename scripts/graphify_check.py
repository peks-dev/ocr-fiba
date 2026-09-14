#!/usr/bin/env python3
"""Read-only validation for the repository's versioned Graphify artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_VERSION = "0.9.26"
CANONICAL_OUTPUTS = (
    "graphify-out/graph.json",
    "graphify-out/GRAPH_REPORT.md",
    "graphify-out/graph.html",
    "graphify-out/manifest.json",
)
SENSITIVE_NAMES = {
    ".env",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "credentials.json",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".kdbx")
SENSITIVE_PARTS = {".aws", ".ssh", ".gnupg", ".kube", ".azure"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_sensitive(path_value: str) -> bool:
    path = PurePosixPath(path_value.replace("\\", "/"))
    name = path.name.lower()
    if name.startswith(".env") and name != ".env.example":
        return True
    return (
        name in SENSITIVE_NAMES
        or name.endswith(SENSITIVE_SUFFIXES)
        or bool(set(part.lower() for part in path.parts) & SENSITIVE_PARTS)
    )


def source_locations(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"source_file", "source_location"} and isinstance(nested, str):
                found.append(nested.split(":", 1)[0])
            else:
                found.extend(source_locations(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(source_locations(nested))
    return found


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    try:
        installed = version("graphifyy")
    except PackageNotFoundError:
        installed = "missing"
    if installed != EXPECTED_VERSION:
        errors.append(
            f"graphifyy {EXPECTED_VERSION} is required; found {installed}. "
            "Run ./scripts/setup-graphify."
        )

    for relative in CANONICAL_OUTPUTS:
        path = root / relative
        if not path.exists():
            errors.append(f"missing canonical output: {relative}")
        elif path.is_symlink() or not path.is_file():
            errors.append(f"canonical output must be a regular file: {relative}")

    graph_path = root / "graphify-out/graph.json"
    manifest_path = root / "graphify-out/manifest.json"
    graph: dict[str, Any] = {}
    manifest: dict[str, Any] = {}

    if graph_path.is_file() and not graph_path.is_symlink():
        try:
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"graph.json is not valid JSON: {exc}")
        else:
            nodes = graph.get("nodes")
            edges = graph.get("links", graph.get("edges"))
            if not isinstance(nodes, list) or not nodes:
                errors.append("graph.json has no nodes")
            if not isinstance(edges, list) or not edges:
                errors.append("graph.json has no edges")

            unsafe_sources = sorted(
                {
                    source
                    for source in source_locations(graph)
                    if Path(source).is_absolute() or is_sensitive(source)
                }
            )
            if unsafe_sources:
                errors.append(
                    "graph.json contains absolute or sensitive source paths: "
                    + ", ".join(unsafe_sources[:5])
                )

    if manifest_path.is_file() and not manifest_path.is_symlink():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"manifest.json is not valid JSON: {exc}")
        else:
            if not isinstance(loaded, dict) or not loaded:
                errors.append("manifest.json is empty or has an invalid schema")
            else:
                manifest = loaded

    manifest_paths: set[str] = set()
    for key, entry in manifest.items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            errors.append("manifest.json contains an invalid entry")
            continue
        relative = PurePosixPath(key)
        candidate = (root / Path(*relative.parts)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append(f"manifest path escapes the repository: {key}")
            continue
        if relative.is_absolute():
            errors.append(f"manifest path is absolute: {key}")
        if is_sensitive(key):
            errors.append(f"manifest contains a sensitive path: {key}")
        manifest_paths.add(relative.as_posix())

    if installed == EXPECTED_VERSION and manifest:
        from graphify.detect import detect

        with tempfile.TemporaryDirectory(prefix="graphify-check-") as cache_dir:
            detection = detect(root, cache_root=Path(cache_dir))
        current_paths = {
            Path(path).resolve().relative_to(root).as_posix()
            for files in detection.get("files", {}).values()
            for path in files
        }

        missing = sorted(current_paths - manifest_paths)
        stale = sorted(manifest_paths - current_paths)
        modified: list[str] = []
        for relative in sorted(current_paths & manifest_paths):
            entry = manifest[relative]
            expected_hash = entry.get("ast_hash") if isinstance(entry, dict) else None
            if not isinstance(expected_hash, str) or not expected_hash:
                modified.append(relative)
                continue
            if md5_file(root / relative) != expected_hash:
                modified.append(relative)

        if missing:
            errors.append("manifest is missing files: " + ", ".join(missing[:10]))
        if stale:
            errors.append("manifest contains removed/excluded files: " + ", ".join(stale[:10]))
        if modified:
            errors.append("manifest hashes do not match sources: " + ", ".join(modified[:10]))
        if detection.get("walk_errors"):
            errors.append("Graphify could not scan the complete repository")

    pending_markers = (
        root / "graphify-out/.needs_update",
        root / "graphify-out/needs_update",
    )
    if any(marker.exists() for marker in pending_markers):
        errors.append("semantic Graphify update is pending")

    report_path = root / "graphify-out/GRAPH_REPORT.md"
    if report_path.is_file() and not report_path.is_symlink():
        report = report_path.read_text(encoding="utf-8")
        if not re.search(r"(?im)^##?\s+God Nodes", report):
            errors.append("GRAPH_REPORT.md has no God Nodes section")

    if errors:
        for message in errors:
            fail(message)
        return 1

    node_count = len(graph.get("nodes", []))
    edge_count = len(graph.get("links", graph.get("edges", [])))
    print(
        f"Graphify check passed: version {installed}, "
        f"{len(manifest_paths)} files, {node_count} nodes, {edge_count} edges."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
