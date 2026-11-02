"""Tests for scripts/alpha_install.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("alpha_install", ROOT / "scripts/alpha_install.py")
tool = importlib.util.module_from_spec(spec)
sys.modules["alpha_install"] = tool
spec.loader.exec_module(tool)

PYPROJECT = {
    "project": {
        "name": "fasthep-flow",
        "dependencies": [
            "numpy>=1.26",
            "fasthep-toolbench[display,http]>=2026.10.1",
            "FastHEP_Render==2026.11.1; python_version >= '3.11'",
            "fasthep-flow>=1",
        ],
        "optional-dependencies": {
            "test": ["pytest>=8", "fasthep-curator==2026.10.1"],
            "distributed": ["fasthep-distributed"],
            "docs": ["sphinx"],
        },
    }
}


def test_fasthep_requirements_become_git_main_and_others_stay():
    result = tool.requirements(PYPROJECT, ["test"], [])
    assert "numpy>=1.26" in result and "pytest>=8" in result
    assert "fasthep-toolbench[display,http] @ git+https://github.com/FAST-HEP/fasthep-toolbench.git@main" in result
    assert "fasthep-curator @ git+https://github.com/FAST-HEP/fasthep-curator.git@main" in result


def test_marker_survives_and_name_is_normalised():
    result = tool.requirements(PYPROJECT, [], [])
    assert (
        "fasthep-render @ git+https://github.com/FAST-HEP/fasthep-render.git@main ; python_version >= '3.11'"
        in result
    )


def test_the_package_itself_is_skipped_and_dev_tools_are_added():
    result = tool.requirements(PYPROJECT, [], [])
    assert not any(item.startswith("fasthep-flow") for item in result)
    assert result[-3:] == ["ruff", "mypy", "build"]


def test_extras_select_groups_and_missing_groups_are_ignored():
    result = tool.requirements(PYPROJECT, ["distributed", "nope"], [])
    assert any(item.startswith("fasthep-distributed @") for item in result)
    assert "pytest>=8" not in result and "sphinx" not in result


def test_extra_packages_and_deduplication():
    result = tool.requirements(PYPROJECT, ["test"], ["fasthep-cli", "fasthep-curator"])
    assert sum(item.startswith("fasthep-curator @") for item in result) == 1
    assert any(item.startswith("fasthep-cli @") for item in result)


def test_print_mode_reads_pyproject(tmp_path, capsys):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fasthep-cli"\ndependencies = ["fasthep-flow>=1", "rich"]\n'
    )
    assert tool.main(["--pyproject", str(tmp_path / "pyproject.toml"), "--print"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("fasthep-flow @ git+") and "rich" in out
