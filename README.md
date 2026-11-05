# FAST-HEP/.github

Shared release machinery for the FAST-HEP package repositories. Forge-neutral Python and
`git-cliff` do the work; the GitHub workflows here are thin wrappers, so a move to another forge
swaps the wrappers only.

| Path | What |
|---|---|
| `cliff.toml` | the one changelog template and commit-to-category rules |
| `scripts/fasthep_changelog.py` | commit check, changelog contract, notes extraction, draft and insert (stdlib only) |
| `docs/commit-convention.md` | commit rules: the subject is the changelog bullet |
| `docs/issues.md` | how to write an issue: the short shape, where detail goes, notes for agents |
| `.github/ISSUE_TEMPLATE/task.md` | the default issue template for every FAST-HEP repository that has none of its own |
| `.pre-commit-hooks.yaml` | `fasthep-commit-msg` hook |
| `.github/workflows/commit-check.yml` | reusable: every commit in a PR follows the convention |
| `.github/workflows/changelog-contract.yml` | reusable: tag `X` needs a dated, non-empty `## [X]` and an empty `## [Unreleased]` |
| `.github/workflows/github-release.yml` | reusable: release notes = the `## [X]` section, plus PyPI link; re-run edits |
| `.github/workflows/package-ci.yml` | reusable: the package's pixi `ci` task per environment; `allow-failure` is the alpha switch |
| `.github/workflows/package-alpha-ci.yml` | reusable, temporary: install with FAST-HEP dependencies from Git `main`, lint, type-check, test; `enabled` is the central off switch |
| `.github/workflows/build-dist.yml` | reusable: build and check sdist and wheel, upload the `distributions` artifact |
| `scripts/alpha_install.py` | rewrites `fasthep-*` requirements to Git `main` for alpha CI |
| `templates/dependabot.yml` | the Dependabot config every package repository carries (Dependabot has no inheritance; `fasthep-dev` `sync-dependabot` copies it) |

## The flow

1. Commits follow `docs/commit-convention.md` (hook locally, CI backstop).
2. At release prep, per package: `fasthep_changelog.py draft X | fasthep_changelog.py insert CHANGELOG.md X --write`
   adds `## [X] - <date>` under `## [Unreleased]`, which stays empty. `draft` refuses when no
   visible commit exists since the last tag.
3. Tag `X`. CD runs `changelog-contract`, then the PyPI publish, then `github-release`.

The workspace pixi tasks (`FAST-HEP/fasthep-dev`) wrap steps 2 and 3 across all packages.

## Adopting it in a package

`.pre-commit-config.yaml`:

```yaml
  - repo: https://github.com/FAST-HEP/.github
    rev: main  # pin to a tag once released
    hooks:
      - id: fasthep-commit-msg
```

Install the commit-msg stage once: `pre-commit install --hook-type commit-msg`.

`.github/workflows/commits.yml`:

```yaml
name: Commits
on: pull_request
jobs:
  commits:
    uses: FAST-HEP/.github/.github/workflows/commit-check.yml@main
```

`.github/workflows/cd.yml` (keep the existing `dist` job; add the two jobs and the `needs`):

```yaml
jobs:
  contract:
    uses: FAST-HEP/.github/.github/workflows/changelog-contract.yml@main
  # dist: ... unchanged
  publish:
    needs: [dist, contract]
    # ... unchanged
  release:
    needs: [publish]
    permissions:
      contents: write
    uses: FAST-HEP/.github/.github/workflows/github-release.yml@main
    with:
      pypi-name: fasthep-flow
```

### Package CI, alpha CI, distribution build

`.github/workflows/ci.yml` (a package whose environments differ passes `matrix`, a JSON list):

```yaml
name: CI
on:
  workflow_dispatch:
  pull_request:
  push:
    branches: [main]
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  ci:
    uses: FAST-HEP/.github/.github/workflows/package-ci.yml@main
```

`.github/workflows/alpha-ci.yml` (inputs `extras`, `extra-packages`, `ruff-args`, `mypy-args`,
`pytest-args` cover the per-package differences):

```yaml
name: Alpha CI
on:
  push:
  pull_request:
jobs:
  alpha-ci:
    uses: FAST-HEP/.github/.github/workflows/package-alpha-ci.yml@main
```

`cd.yml`: the `dist` job becomes `uses: FAST-HEP/.github/.github/workflows/build-dist.yml@main`.
The `publish` job stays in the package: PyPI trusted publishing does not support a reusable
workflow as the publisher.

To make CI strict when alpha ends, change the `allow-failure` default in `package-ci.yml`; to retire
alpha CI everywhere, change the `enabled` default in `package-alpha-ci.yml` to `false`.

## Develop

```bash
pixi run test
pixi run lint
```

Callers must be able to read this repository: keep it public, or allow access under the
repository's Actions settings.
