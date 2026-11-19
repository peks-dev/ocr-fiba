from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {
    ".agents",
    ".claude",
    ".codex",
    ".devin",
    ".engram",
    ".git",
    ".graphify-venv",
    ".next",
    ".pi",
    ".pytest_cache",
    ".server",
    ".venv",
    "__pycache__",
    "dataset",
    "graphify-out",
    "node_modules",
    "outputs",
    "runs",
}
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*$")
LINK_RE = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(([^)\n]+)\)")
FENCE_RE = re.compile(r"^\s*([`~]{3,})")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def iter_markdown_files(root: Path = REPO_ROOT) -> list[Path]:
    """Return tracked/source Markdown files outside ignored/generated directories."""
    markdown_files: list[Path] = []
    for current_dir, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_PARTS)
        for filename in sorted(filenames):
            if filename.endswith(".md"):
                markdown_files.append(Path(current_dir) / filename)
    return markdown_files


def strip_fenced_code_blocks(text: str) -> list[str]:
    """Return lines outside fenced code blocks."""
    visible_lines: list[str] = []
    fence_char: str | None = None
    fence_len = 0

    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if fence_char is None:
            if match:
                fence_char = match.group(1)[0]
                fence_len = len(match.group(1))
                continue
            visible_lines.append(line)
        else:
            if match and match.group(1)[0] == fence_char and len(match.group(1)) >= fence_len:
                fence_char = None
                fence_len = 0

    return visible_lines


def github_slug(heading: str) -> str:
    """Approximate GitHub Flavored Markdown heading anchor generation."""
    without_links = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading)
    normalized = without_links.replace("`", "").strip().lower()
    cleaned = "".join(ch for ch in normalized if ch.isalnum() or ch in {" ", "-", "_"})
    return cleaned.replace(" ", "-")


def extract_heading_anchors(path: Path) -> set[str]:
    """Extract all GFM heading anchors from a Markdown file."""
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    lines = strip_fenced_code_blocks(path.read_text(encoding="utf-8"))

    for line in lines:
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = github_slug(match.group(1).rstrip("#").strip())
        if not base:
            continue
        seen = counts.get(base, 0)
        anchors.add(base if seen == 0 else f"{base}-{seen}")
        counts[base] = seen + 1

    return anchors


def extract_relative_targets(path: Path) -> list[str]:
    """Extract non-external link/image targets outside code fences and inline code."""
    lines = strip_fenced_code_blocks(path.read_text(encoding="utf-8"))
    targets: list[str] = []

    for line in lines:
        scrubbed = INLINE_CODE_RE.sub("", line)
        for match in LINK_RE.finditer(scrubbed):
            raw_target = match.group(1).strip()
            if not raw_target:
                continue
            if raw_target.startswith("<") and ">" in raw_target:
                target = raw_target[1 : raw_target.index(">")].strip()
            else:
                target = re.split(r'\s+(?=["\'])', raw_target, maxsplit=1)[0].strip()
            if not target or target.lower().startswith(EXTERNAL_PREFIXES):
                continue
            targets.append(target)

    return targets


class DocsLinksTest(unittest.TestCase):
    def test_slug_and_link_extraction_ignore_code_examples(self) -> None:
        self.assertEqual(github_slug("Core Pipeline & `PipelineConfig`"), "core-pipeline--pipelineconfig")

        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "sample.md"
            doc.write_text(
                "# Intro\n"
                "# Intro\n"
                "```markdown\n"
                "[ignored](does-not-exist.md)\n"
                "# Ignored Heading\n"
                "```\n"
                "Inline `[also-ignored](missing.md)` and [real](target.md#intro-1) "
                "and [ext](https://example.com) and ![img](pic.png \"title\").\n",
                encoding="utf-8",
            )
            self.assertEqual(extract_heading_anchors(doc), {"intro", "intro-1"})
            self.assertEqual(extract_relative_targets(doc), ["target.md#intro-1", "pic.png"])

    def test_relative_markdown_links_and_anchors_resolve(self) -> None:
        markdown_files = iter_markdown_files()
        self.assertGreater(len(markdown_files), 0)

        anchor_cache: dict[Path, set[str]] = {}
        broken: list[str] = []

        for source_file in markdown_files:
            source_rel = source_file.relative_to(REPO_ROOT).as_posix()
            for target in extract_relative_targets(source_file):
                path_part, _, fragment = target.partition("#")
                target_path = (source_file.parent / path_part).resolve() if path_part else source_file.resolve()

                if not target_path.is_relative_to(REPO_ROOT):
                    broken.append(f"{source_rel} -> {target} (escapes repository root)")
                    continue

                if not target_path.exists():
                    broken.append(f"{source_rel} -> {target} (missing target)")
                    continue

                if fragment and target_path.is_file() and target_path.suffix.lower() == ".md":
                    anchors = anchor_cache.setdefault(target_path, extract_heading_anchors(target_path))
                    if fragment not in anchors:
                        broken.append(f"{source_rel} -> {target} (missing heading #{fragment})")

        self.assertEqual(broken, [], "Broken Markdown links/anchors found:\n" + "\n".join(broken))
