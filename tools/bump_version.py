#!/usr/bin/env python3
"""
OrbVis version bump tool.

Reads git log since the last tag, auto-categorizes commits into changelog
sections, opens $EDITOR for review, then writes VERSION and CHANGELOG.md.

Usage:
    python tools/bump_version.py <new_version>
    python tools/bump_version.py 0.2.0
"""

import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
VERSION_FILE = REPO_ROOT / "VERSION"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"

# Static version locations kept in sync with VERSION.
# Each entry: (relative path, line-anchored regex template, expected match count).
# `{old}` is substituted with re.escape(old_version) so we only ever replace the
# exact previous version literal — dependency `"version"` fields in package-lock
# stay untouched even if a transitive dep happens to share the version string.
STATIC_VERSION_FILES: list[tuple[str, str, int]] = [
    ("backend/pyproject.toml", r'(?m)^(version\s*=\s*"){old}(")', 1),
    ("cmk_plugins/pyproject.toml", r'(?m)^(version\s*=\s*"){old}(")', 1),
    ("frontend/package.json", r'(?m)^(\s*"version":\s*"){old}(")', 1),
    # package-lock.json carries the project version at the JSON root AND inside
    # the `packages[""]` self-entry. Both appear before any dependency block.
    ("frontend/package-lock.json", r'(?m)^(\s*"version":\s*"){old}(")', 2),
]

# Commit verb → changelog category
CATEGORY_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(add|introduce|implement|support|enable|create|new)\b", re.I), "Added"),
    (re.compile(r"^(fix|correct|resolve|repair|patch)\b", re.I), "Fixed"),
    (re.compile(r"^(remove|delete|drop|clean|rip)\b", re.I), "Removed"),
    (re.compile(r"^(deprecate)\b", re.I), "Deprecated"),
    (re.compile(r"^(security|cve)\b", re.I), "Security"),
]
CATEGORY_ORDER = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]

# Scopes to skip (pure internal / no user impact)
SKIP_SCOPES = {"chore", "ci", "test", "style", "docs", "refactor", "lint", "typo"}


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=REPO_ROOT, text=True).strip()


def last_tag() -> str | None:
    try:
        return run(["git", "describe", "--tags", "--abbrev=0"])
    except subprocess.CalledProcessError:
        return None


def tag_exists(tag: str) -> bool:
    return bool(run(["git", "tag", "-l", tag]))


def parse_version(v: str) -> tuple[int, int, int]:
    major, minor, patch = v.split(".")
    return int(major), int(minor), int(patch)


def commits_since(ref: str | None) -> list[tuple[str, str]]:
    """Return list of (hash, subject) since ref (or all commits if None)."""
    range_arg = f"{ref}..HEAD" if ref else "HEAD"
    out = run(["git", "log", "--no-merges", "--format=%H\t%s", range_arg])
    if not out:
        return []
    result = []
    for line in out.splitlines():
        h, _, subject = line.partition("\t")
        result.append((h[:8], subject))
    return result


def categorize(subject: str) -> tuple[str, str]:
    """Return (category, formatted entry) for a commit subject."""
    # Extract verb: everything after "scope: "
    scope_match = re.match(r"^[\w/-]+:\s*(.+)$", subject)
    verb_phrase = scope_match.group(1) if scope_match else subject

    for pattern, category in CATEGORY_RULES:
        if pattern.match(verb_phrase):
            return category, verb_phrase

    return "Changed", verb_phrase


def build_entry(version: str, commits: list[tuple[str, str]]) -> str:
    today = date.today().isoformat()
    sections: dict[str, list[str]] = {cat: [] for cat in CATEGORY_ORDER}

    for _hash, subject in commits:
        # Derive scope
        scope_match = re.match(r"^([\w/-]+):", subject)
        scope = scope_match.group(1).lower() if scope_match else ""
        if scope in SKIP_SCOPES:
            continue

        category, entry = categorize(subject)
        # Capitalize first letter
        entry = entry[0].upper() + entry[1:]
        sections[category].append(f"- {entry}")

    lines = [f"## [{version}] - {today}", ""]
    for cat in CATEGORY_ORDER:
        if sections[cat]:
            lines.append(f"### {cat}")
            lines.extend(sections[cat])
            lines.append("")

    return "\n".join(lines)


def open_in_editor(content: str) -> str:
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        subprocess.call([editor, tmp])
        return Path(tmp).read_text()
    finally:
        Path(tmp).unlink(missing_ok=True)


def update_static_versions(old_version: str, new_version: str) -> list[Path]:
    """Rewrite the version literal in every file listed in STATIC_VERSION_FILES.

    Aborts the whole bump if any file is missing or doesn't contain the
    expected number of matches — a partial bump would silently drift.
    """
    old_q = re.escape(old_version)
    updated: list[Path] = []
    for rel, template, expected in STATIC_VERSION_FILES:
        path = REPO_ROOT / rel
        if not path.exists():
            print(f"Refusing to bump: {rel} not found.")
            sys.exit(1)
        content = path.read_text()
        pattern = re.compile(template.format(old=old_q))
        new_content, n = pattern.subn(rf"\g<1>{new_version}\g<2>", content, count=expected)
        if n != expected:
            print(
                f"Refusing to bump: expected {expected} match(es) of version "
                f"{old_version!r} in {rel}, found {n}."
            )
            sys.exit(1)
        path.write_text(new_content)
        updated.append(path)
    return updated


def prepend_to_changelog(entry: str) -> None:
    original = CHANGELOG_FILE.read_text()
    # Insert after the header block (before first "## [")
    marker = "\n## ["
    idx = original.find(marker)
    if idx == -1:
        CHANGELOG_FILE.write_text(original.rstrip() + "\n\n" + entry.strip() + "\n")
    else:
        CHANGELOG_FILE.write_text(original[:idx] + "\n\n" + entry.strip() + original[idx:])


def main() -> None:
    if len(sys.argv) != 2 or not re.match(r"^\d+\.\d+\.\d+$", sys.argv[1]):
        print(__doc__)
        sys.exit(1)

    new_version = sys.argv[1]
    current_version = VERSION_FILE.read_text().strip()
    tag = last_tag()

    print(f"Current version : {current_version}")
    print(f"New version     : {new_version}")
    print(f"Last git tag    : {tag or '(none — using full history)'}")
    print()

    new_tag = f"v{new_version}"
    if tag_exists(new_tag):
        print(
            f"Refusing to bump: git tag {new_tag} already exists.\n"
            "Pick a higher version — Checkmk Exchange rejects re-uploads of an existing version."
        )
        sys.exit(1)

    if parse_version(new_version) <= parse_version(current_version):
        print(
            f"Refusing to bump: {new_version} is not greater than current {current_version}.\n"
            "Versions must be strictly monotonic."
        )
        sys.exit(1)

    commits = commits_since(tag)
    if not commits:
        print("No commits found since last tag.")
        sys.exit(0)

    print(f"Found {len(commits)} commit(s). Opening editor…\n")

    entry = build_entry(new_version, commits)
    edited = open_in_editor(entry)

    if not edited.strip():
        print("Empty entry — aborting.")
        sys.exit(1)

    print("\n--- Changelog entry ---")
    print(edited.strip())
    print("-----------------------\n")

    answer = (
        input(f"Write VERSION={new_version} and prepend to CHANGELOG.md? [y/N] ").strip().lower()
    )
    if answer != "y":
        print("Aborted.")
        sys.exit(0)

    VERSION_FILE.write_text(new_version + "\n")
    prepend_to_changelog(edited)
    static_updated = update_static_versions(current_version, new_version)

    print(f"\nDone. VERSION={new_version}, CHANGELOG.md updated.")
    print("Also bumped:")
    for path in static_updated:
        print(f"  - {path.relative_to(REPO_ROOT)}")
    print("\nNext steps — copy & paste:\n")
    add_paths = " ".join(
        ["VERSION", "CHANGELOG.md", *[str(p.relative_to(REPO_ROOT)) for p in static_updated]]
    )
    print(f"  git add {add_paths}")
    print(f"  git commit -m 'version: bump to {new_version}'")
    print(f"  git tag v{new_version}")
    print("  git push && git push --tags")


if __name__ == "__main__":
    main()
