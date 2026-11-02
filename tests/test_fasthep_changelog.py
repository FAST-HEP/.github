"""Tests for scripts/fasthep_changelog.py. The cliff tests build a throwaway git repository."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("fasthep_changelog", ROOT / "scripts/fasthep_changelog.py")
tool = importlib.util.module_from_spec(spec)
sys.modules["fasthep_changelog"] = tool
spec.loader.exec_module(tool)

CHANGELOG = """# Changelog

Preamble.

## [Unreleased]

## [2026.11.1] - 2026-11-02

### Added

- First thing.

### Fixed

- Second thing.

## [2026.10.1] - 2026-10-26

### Added

- Old thing.

[2026.10.1]: https://example.org/2026.10.1
"""


# --- commit messages -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "feat: add a thing",
        "fix(compiler): chunk each file by its own event count",
        "feat(cli)!: drop the old flag",
        "deps(deps-dev): Bump ruff from 0.8 to 0.9",
        "ci(deps): Bump actions/checkout from 6 to 7",
        "docs(CHANGELOG): add 2026.11.1 release".replace("CHANGELOG", "changelog"),
        "Merge pull request #1 from FAST-HEP/x",
        "fix: x\n\nBody.\n\nChangelog: security\nCo-Authored-By: A <a@b.c>",
    ],
)
def test_valid_messages(message):
    assert tool.validate_message(message) == []


@pytest.mark.parametrize(
    "message",
    [
        "",
        "add a thing",
        "feature: add a thing",
        "feat:no space",
        "feat(Scope): upper scope",
        "fix: x\n\nChangelog: nonsense",
    ],
)
def test_invalid_messages(message):
    assert tool.validate_message(message)


def test_hook_allows_fixup_and_comments_but_ci_does_not():
    assert tool.validate_message("fixup! feat: x", hook=True) == []
    assert tool.validate_message("fixup! feat: x")
    assert tool.validate_message("# comment\nfeat: x\n# another", hook=True) == []


def test_commit_msg_exit_code(tmp_path):
    good = tmp_path / "good"
    good.write_text("feat: x\n")
    bad = tmp_path / "bad"
    bad.write_text("nope\n")
    assert tool.main(["commit-msg", str(good)]) == 0
    assert tool.main(["commit-msg", str(bad)]) == 1


# --- sections --------------------------------------------------------------------------------


def test_check_passes_on_a_good_changelog():
    assert tool.check(CHANGELOG, "2026.11.1") == []


def test_check_missing_section():
    assert any("no `## [2026.12.1]`" in p for p in tool.check(CHANGELOG, "2026.12.1"))


def test_check_unreleased_not_empty():
    text = CHANGELOG.replace("## [Unreleased]\n", "## [Unreleased]\n\n### Added\n\n- Leftover.\n")
    assert any("Unreleased" in p for p in tool.check(text, "2026.11.1"))


def test_check_empty_section_and_missing_date():
    text = CHANGELOG.replace("- First thing.\n", "").replace("- Second thing.\n", "")
    assert any("no entries" in p for p in tool.check(text, "2026.11.1"))
    undated = CHANGELOG.replace("[2026.11.1] - 2026-11-02", "[2026.11.1]")
    assert any("YYYY-MM-DD" in p for p in tool.check(undated, "2026.11.1"))


def test_extract_stops_at_next_heading_and_drops_link_definitions():
    body = tool.extract(CHANGELOG, "2026.11.1")
    assert body.startswith("### Added") and "Second thing." in body and "Old thing" not in body
    last = tool.extract(CHANGELOG, "2026.10.1")
    assert last.endswith("- Old thing.")


def test_extract_errors():
    with pytest.raises(tool.ToolError):
        tool.extract(CHANGELOG, "2099.01.1")


def test_release_notes_cli(tmp_path, capsys):
    f = tmp_path / "CHANGELOG.md"
    f.write_text(CHANGELOG)
    assert tool.main(["release-notes", str(f), "2026.11.1", "--pypi", "fasthep-flow"]) == 0
    out = capsys.readouterr().out
    assert "- First thing." in out
    assert "https://pypi.org/project/fasthep-flow/2026.11.1/" in out
    assert "pip install fasthep-flow==2026.11.1" in out


def test_insert_goes_under_unreleased_and_keeps_the_rest():
    section = "## [2026.12.1] - 2026-12-01\n\n### Added\n\n- New.\n"
    result = tool.insert(CHANGELOG, "2026.12.1", section)
    assert result.index("## [Unreleased]") < result.index("## [2026.12.1]") < result.index("## [2026.11.1]")
    assert result.count("## [Unreleased]") == 1
    assert tool.check(result, "2026.12.1") == []
    assert "Preamble." in result and result.endswith("\n") and "\n\n\n" not in result


def test_insert_refuses_duplicates_and_dirty_unreleased():
    with pytest.raises(tool.ToolError):
        tool.insert(CHANGELOG, "2026.11.1", "## [2026.11.1] - x\n- a\n")
    dirty = CHANGELOG.replace("## [Unreleased]\n", "## [Unreleased]\n\n- Leftover.\n")
    with pytest.raises(tool.ToolError):
        tool.insert(dirty, "2026.12.1", "## [2026.12.1] - x\n- a\n")


def test_insert_dry_run_writes_nothing(tmp_path, capsys):
    f = tmp_path / "CHANGELOG.md"
    f.write_text(CHANGELOG)
    src = tmp_path / "section.md"
    src.write_text("## [2026.12.1] - 2026-12-01\n\n- New.\n")
    assert tool.main(["insert", str(f), "2026.12.1", "--from", str(src)]) == 0
    assert f.read_text() == CHANGELOG
    assert tool.main(["insert", str(f), "2026.12.1", "--from", str(src), "--write"]) == 0
    assert "## [2026.12.1]" in f.read_text()


# --- git: commit range and cliff -------------------------------------------------------------


def git(repo: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env
    ).stdout


def commit(repo: Path, message: str) -> None:
    (repo / "f.txt").write_text(message)
    git(repo, "add", "f.txt")
    git(repo, "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    commit(tmp_path, "feat: before the tag")
    git(tmp_path, "tag", "2026.10.1")
    return tmp_path


def test_commits_range(repo, capsys):
    commit(repo, "feat: fine")
    assert tool.main(["commits", "2026.10.1..HEAD", "--repo", str(repo)]) == 0
    commit(repo, "oops not conventional")
    commit(repo, "fixup! feat: fine")
    assert tool.main(["commits", "2026.10.1..HEAD", "--repo", str(repo)]) == 1
    err = capsys.readouterr().err
    assert "oops not conventional" in err and "fixup!" in err


needs_cliff = pytest.mark.skipif(shutil.which("git-cliff") is None, reason="git-cliff not installed")


@needs_cliff
def test_cliff_groups_order_and_markers(repo):
    commit(repo, "fix(compiler): chunk each file by its own count")
    commit(repo, "feat(cli): add a flag")
    commit(repo, "refactor: tidy the loader")
    commit(repo, "feat(render)!: rename the style option")
    commit(repo, "chore: bump pins")
    commit(repo, "deps(deps): Bump ruff from 0.8 to 0.9")
    commit(repo, "docs: reword the readme")
    commit(repo, "feat: hidden by trailer\n\nChangelog: skip")
    commit(repo, "fix: drop the old reader\n\nChangelog: removed")
    commit(repo, "fix: old call is going away\n\nChangelog: deprecated")
    commit(repo, "fix: validate tokens\n\nChangelog: security")
    section = tool.draft("2026.12.1", str(repo), ROOT / "cliff.toml")
    lines = [line for line in section.splitlines() if line]
    assert lines[0].startswith("## [2026.12.1] - ")
    assert [line for line in lines if line.startswith("###")] == [
        "### Added",
        "### Changed",
        "### Deprecated",
        "### Removed",
        "### Fixed",
        "### Security",
    ]
    assert "- **cli**: Add a flag" in section
    assert "- **Breaking**: **render**: Rename the style option" in section
    assert "- Tidy the loader" in section
    assert "- **compiler**: Chunk each file by its own count" in section
    assert "- Drop the old reader" in section
    for hidden in ("Bump ruff", "bump pins", "reword the readme", "hidden by trailer", "before the tag"):
        assert hidden not in section
    # the drafted section satisfies the contract once inserted
    result = tool.insert(CHANGELOG, "2026.12.1", section)
    assert tool.check(result, "2026.12.1") == []


@needs_cliff
def test_cliff_nothing_visible_is_an_error(repo):
    commit(repo, "docs: only docs")
    commit(repo, "chore: only chore")
    with pytest.raises(tool.ToolError, match="nothing to release"):
        tool.draft("2026.12.1", str(repo), ROOT / "cliff.toml")


def test_workflows_are_valid_yaml_and_reusable():
    yaml = pytest.importorskip("yaml")
    for name in (
        "commit-check",
        "changelog-contract",
        "github-release",
        "package-ci",
        "package-alpha-ci",
        "build-dist",
    ):
        doc = yaml.safe_load((ROOT / f".github/workflows/{name}.yml").read_text())
        assert "workflow_call" in doc[True], name  # PyYAML reads the key `on` as True
        assert doc["jobs"], name
