# FAST-HEP/.github

Shared release machinery for the FAST-HEP package repositories. Forge-neutral Python and
`git-cliff` do the work; the GitHub workflows here are thin wrappers, so a move to another forge
swaps the wrappers only.

| Path | What |
|---|---|
| `cliff.toml` | the one changelog template and commit-to-category rules |
| `scripts/fasthep_changelog.py` | commit check, changelog contract, notes extraction, draft and insert (stdlib only) |
| `docs/commit-convention.md` | commit rules: the subject is the changelog bullet |
| `.pre-commit-hooks.yaml` | `fasthep-commit-msg` hook |
| `.github/workflows/commit-check.yml` | reusable: every commit in a PR follows the convention |
| `.github/workflows/changelog-contract.yml` | reusable: tag `X` needs a dated, non-empty `## [X]` and an empty `## [Unreleased]` |
| `.github/workflows/github-release.yml` | reusable: release notes = the `## [X]` section, plus PyPI link; re-run edits |

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

## Develop

```bash
pixi run test
pixi run lint
```

Callers must be able to read this repository: keep it public, or allow access under the
repository's Actions settings.
