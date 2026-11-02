#!/usr/bin/env python3
"""FAST-HEP changelog and release-notes tooling, shared by every package repository.

Standard library only, forge-neutral: CI workflows and local pixi tasks both call this file.
Rules live in docs/commit-convention.md; the changelog template is cliff.toml.

Subcommands:
  commit-msg FILE        validate a commit message file (pre-commit commit-msg hook)
  commits RANGE          validate every commit in a git range (CI backstop)
  check CHANGELOG X      contract: a dated, non-empty `## [X]` section and an empty Unreleased
  extract CHANGELOG X    print the body of the `## [X]` section
  release-notes CHANGELOG X  print the release notes for X (section body plus the PyPI link)
  draft X                run git-cliff for the commits since the last tag, print the section
  insert CHANGELOG X     put a drafted section (stdin or --from) under `## [Unreleased]`
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TYPES = (
    "feat",
    "fix",
    "refactor",
    "perf",
    "docs",
    "chore",
    "ci",
    "build",
    "test",
    "style",
    "release",
    "revert",
    "deps",
)
CHANGELOG_VALUES = ("skip", "deprecated", "removed", "security")
TEMP_PREFIXES = ("fixup! ", "squash! ", "amend! ")

SUBJECT_RE = re.compile(
    r"^(?P<type>[a-z]+)(\((?P<scope>[a-z0-9_./-]+)\))?(?P<bang>!)?: (?P<desc>\S.*)$"
)
TRAILER_RE = re.compile(r"^Changelog:(?P<value>.*)$")
HEADING_RE = re.compile(r"^## \[(?P<name>[^\]]+)\](?P<rest>.*)$")
DATED_RE = re.compile(r"^ - \d{4}-\d{2}-\d{2}\s*$")
LINK_DEF_RE = re.compile(r"^\[[^\]]+\]: ")
BULLET_RE = re.compile(r"^\s*[-*] \S")

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "cliff.toml"


class ToolError(Exception):
    """A rule failed; the message says what to fix."""


# --- commit messages -------------------------------------------------------------------------


def validate_message(message: str, *, hook: bool = False) -> list[str]:
    """Return the problems with a commit message (empty list: fine).

    ``hook`` is for the commit-msg hook: comment lines are dropped and fixup!/squash! subjects
    pass, since they disappear before the history is shared.
    """
    lines = message.splitlines()
    if hook:
        lines = [line for line in lines if not line.startswith("#")]
    body = [line for line in lines if line.strip()]
    if not body:
        return ["empty commit message"]
    subject = body[0]
    if subject.startswith("Merge "):
        return []
    if hook and subject.startswith(TEMP_PREFIXES):
        return []
    problems = []
    match = SUBJECT_RE.match(subject)
    if not match:
        problems.append(
            f"subject does not match `<type>(<scope>)!: <description>`: {subject!r}"
        )
    elif match["type"] not in TYPES:
        problems.append(
            f"unknown type {match['type']!r}; use one of {', '.join(TYPES)}"
        )
    for line in lines[1:]:
        trailer = TRAILER_RE.match(line)
        if trailer and trailer["value"].strip() not in CHANGELOG_VALUES:
            problems.append(
                f"bad trailer {line!r}; `Changelog:` takes {', '.join(CHANGELOG_VALUES)}"
            )
    return problems


def cmd_commit_msg(args: argparse.Namespace) -> int:
    problems = validate_message(Path(args.file).read_text(encoding="utf-8"), hook=True)
    for problem in problems:
        print(f"commit message: {problem}", file=sys.stderr)
    if problems:
        print("See docs/commit-convention.md in FAST-HEP/.github.", file=sys.stderr)
    return 1 if problems else 0


def cmd_commits(args: argparse.Namespace) -> int:
    out = subprocess.run(
        ["git", "-C", args.repo, "log", "--no-merges", "--format=%h%x1f%B%x1e", args.range],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    failed = 0
    count = 0
    for record in out.split("\x1e"):
        if not record.strip():
            continue
        short, _, message = record.strip().partition("\x1f")
        count += 1
        problems = validate_message(message)
        if message.startswith(TEMP_PREFIXES):
            problems.append("fixup!/squash! commit: fold it into its target before merging")
        for problem in problems:
            print(f"{short}: {problem}", file=sys.stderr)
        failed += bool(problems)
    print(f"checked {count} commit(s) in {args.range}: {failed} failing")
    return 1 if failed else 0


# --- changelog sections ----------------------------------------------------------------------


def _sections(lines: list[str]) -> list[tuple[str, str, int, int]]:
    """(name, text after the bracket, first line, end line) for every `## [..]` heading."""
    starts = [
        (i, m["name"], m["rest"])
        for i, line in enumerate(lines)
        if (m := HEADING_RE.match(line))
    ]
    ends = [s[0] for s in starts[1:]] + [len(lines)]
    return [(name, rest, i, end) for (i, name, rest), end in zip(starts, ends)]


def _body(lines: list[str], start: int, end: int) -> str:
    chunk = [line for line in lines[start + 1 : end] if not LINK_DEF_RE.match(line)]
    return "\n".join(chunk).strip()


def find_section(text: str, name: str) -> tuple[str, str, int, int] | None:
    lines = text.splitlines()
    for section in _sections(lines):
        if section[0] == name:
            return section
    return None


def extract(text: str, version: str) -> str:
    section = find_section(text, version)
    if section is None:
        raise ToolError(f"CHANGELOG.md has no `## [{version}]` section")
    body = _body(text.splitlines(), section[2], section[3])
    if not any(BULLET_RE.match(line) for line in body.splitlines()):
        raise ToolError(f"the `## [{version}]` section has no entries")
    return body


def check(text: str, version: str) -> list[str]:
    problems = []
    section = find_section(text, version)
    if section is None:
        problems.append(f"no `## [{version}]` section (run the changelog step before tagging)")
    else:
        if not DATED_RE.match(section[1]):
            problems.append(f"`## [{version}]` heading needs ` - YYYY-MM-DD` after it")
        lines = text.splitlines()
        if not any(BULLET_RE.match(line) for line in lines[section[2] + 1 : section[3]]):
            problems.append(f"`## [{version}]` has no entries: a release needs real changes")
    unreleased = find_section(text, "Unreleased")
    if unreleased and _body(text.splitlines(), unreleased[2], unreleased[3]):
        problems.append("`## [Unreleased]` is not empty: its entries belong to a release section")
    return problems


def cmd_check(args: argparse.Namespace) -> int:
    problems = check(Path(args.changelog).read_text(encoding="utf-8"), args.version)
    for problem in problems:
        print(f"{args.changelog}: {problem}", file=sys.stderr)
    if not problems:
        print(f"{args.changelog}: contract holds for {args.version}")
    return 1 if problems else 0


def cmd_extract(args: argparse.Namespace) -> int:
    print(extract(Path(args.changelog).read_text(encoding="utf-8"), args.version))
    return 0


def cmd_release_notes(args: argparse.Namespace) -> int:
    notes = extract(Path(args.changelog).read_text(encoding="utf-8"), args.version)
    if args.pypi:
        notes += (
            f"\n\nPyPI: https://pypi.org/project/{args.pypi}/{args.version}/"
            f"\n\nInstall: `pip install {args.pypi}=={args.version}`"
        )
    print(notes)
    return 0


# --- draft and insert ------------------------------------------------------------------------


def draft(version: str, repo: str, config: Path) -> str:
    result = subprocess.run(
        [
            "git-cliff",
            "--config",
            str(config),
            "--unreleased",
            "--tag",
            version,
            "--strip",
            "all",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo,  # not --repository: git-cliff cannot open a submodule checkout that way
    )
    if result.returncode:
        raise ToolError(f"git-cliff failed: {result.stderr.strip()}")
    section = re.sub(r"\n{3,}", "\n\n", result.stdout.strip())
    if not any(BULLET_RE.match(line) for line in section.splitlines()):
        raise ToolError(
            f"no visible commits since the last tag in {repo}: nothing to release "
            "(docs/chore/ci/build/test/style only)"
        )
    return section + "\n"


def cmd_draft(args: argparse.Namespace) -> int:
    sys.stdout.write(draft(args.version, args.repo, Path(args.config)))
    return 0


def insert(text: str, version: str, section: str) -> str:
    if find_section(text, version):
        raise ToolError(f"`## [{version}]` already exists")
    unreleased = find_section(text, "Unreleased")
    if unreleased is None:
        raise ToolError("CHANGELOG.md has no `## [Unreleased]` heading to insert under")
    lines = text.splitlines()
    if _body(lines, unreleased[2], unreleased[3]):
        raise ToolError("`## [Unreleased]` is not empty: split it by hand first")
    head = lines[: unreleased[2] + 1]
    tail = lines[unreleased[2] + 1 :]
    while tail and not tail[0].strip():
        tail.pop(0)
    return "\n".join([*head, "", *section.strip().splitlines(), "", *tail]).rstrip() + "\n"


def cmd_insert(args: argparse.Namespace) -> int:
    path = Path(args.changelog)
    section = Path(args.source).read_text(encoding="utf-8") if args.source else sys.stdin.read()
    result = insert(path.read_text(encoding="utf-8"), args.version, section)
    if args.write:
        path.write_text(result, encoding="utf-8")
        print(f"{path}: added `## [{args.version}]`")
    else:
        print(f"dry run: would add `## [{args.version}]` to {path}; pass --write to apply")
        sys.stdout.write(section)
    return 0


# --- cli -------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("commit-msg", help="validate a commit message file")
    p.add_argument("file")
    p.set_defaults(func=cmd_commit_msg)

    p = sub.add_parser("commits", help="validate every commit in a git range")
    p.add_argument("range", help="e.g. origin/main..HEAD")
    p.add_argument("--repo", default=".")
    p.set_defaults(func=cmd_commits)

    for name, func, helptext in (
        ("check", cmd_check, "contract check for a release version"),
        ("extract", cmd_extract, "print the body of a release section"),
        ("release-notes", cmd_release_notes, "print the release notes"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("changelog")
        p.add_argument("version")
        if name == "release-notes":
            p.add_argument("--pypi", help="distribution name, adds the PyPI link")
        p.set_defaults(func=func)

    p = sub.add_parser("draft", help="git-cliff section for the commits since the last tag")
    p.add_argument("version")
    p.add_argument("--repo", default=".")
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("insert", help="insert a section under `## [Unreleased]`")
    p.add_argument("changelog")
    p.add_argument("version")
    p.add_argument("--from", dest="source", help="file with the section (default: stdin)")
    p.add_argument("--write", action="store_true", help="apply (default is a dry run)")
    p.set_defaults(func=cmd_insert)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
