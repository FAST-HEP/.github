#!/usr/bin/env python3
"""Install a FAST-HEP package's dependencies for alpha CI: FAST-HEP ones from Git `main`.

Reads ``pyproject.toml`` in the current directory, takes ``project.dependencies`` plus the chosen
optional-dependency groups (``--extras test,distributed``; a missing group is ignored) and the dev
tools (ruff, mypy, build), rewrites every ``fasthep-*`` requirement to
``<name>[extras] @ git+https://github.com/FAST-HEP/<name>.git@main`` (a pin or version range
is dropped: alpha CI tests against the development head), and runs ``pip install``. The package
itself is skipped; install it afterwards with ``pip install -e . --no-deps``.

``--extra-packages`` adds FAST-HEP distributions the package does not declare. ``--print`` shows the
requirements instead of installing them. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

FASTHEP_RE = re.compile(
    r"^\s*(?P<name>fasthep[-_.][A-Za-z0-9_.-]+)(?P<extras>\[[^\]]+\])?", re.IGNORECASE
)
DEV_TOOLS = ("ruff", "mypy", "build")


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def git_requirement(name: str, extras: str = "", marker: str = "") -> str:
    requirement = f"{name}{extras} @ git+https://github.com/FAST-HEP/{name}.git@main"
    return f"{requirement} ; {marker}" if marker else requirement


def resolve(requirement: str, own_name: str) -> str | None:
    """The requirement to install, or None to skip it (the package itself)."""
    match = FASTHEP_RE.match(requirement)
    if not match:
        return requirement
    name = normalise(match["name"])
    if name == own_name:
        return None
    marker = requirement.partition(";")[2].strip()
    return git_requirement(name, match["extras"] or "", marker)


def requirements(pyproject: dict, extras: list[str], extra_packages: list[str]) -> list[str]:
    project = pyproject["project"]
    own_name = normalise(project["name"])
    optional = project.get("optional-dependencies", {})
    wanted = list(project.get("dependencies", []))
    for group in extras:
        wanted.extend(optional.get(group, []))
    wanted.extend(extra_packages)
    resolved: list[str] = []
    for requirement in [*wanted, *DEV_TOOLS]:
        item = resolve(requirement, own_name)
        if item is not None and item not in resolved:
            resolved.append(item)
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--extras", default="test", help="comma-separated optional-dependency groups")
    parser.add_argument("--extra-packages", nargs="*", default=[], help="more FAST-HEP distributions")
    parser.add_argument("--print", action="store_true", help="print the requirements, install nothing")
    args = parser.parse_args(argv)

    with Path(args.pyproject).open("rb") as handle:
        pyproject = tomllib.load(handle)
    extras = [group.strip() for group in args.extras.split(",") if group.strip()]
    resolved = requirements(pyproject, extras, args.extra_packages)
    if args.print:
        print("\n".join(resolved))
        return 0
    return subprocess.call([sys.executable, "-m", "pip", "install", *resolved])


if __name__ == "__main__":
    sys.exit(main())
