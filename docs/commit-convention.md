# FAST-HEP commit convention

The commit history is the source of every changelog and release note. `git-cliff`
(`cliff.toml`) turns commits into the `## [X]` section of `CHANGELOG.md`; nobody edits that section
afterwards. So **the commit subject is the changelog bullet**: write it for a user of the package.

## Subject

```
<type>(<scope>)!: <description>
```

- `<type>`: one of the table below. Lowercase.
- `(<scope>)`: optional, lowercase (`a-z 0-9 _ . / -`), the part of the package a user knows
  (`compiler`, `cli`, `render`). It becomes a bold prefix in the changelog.
- `!`: optional, marks a breaking change. The entry goes under **Changed**, prefixed `**Breaking**`.
- `<description>`: start with a verb ("add", "fix", "accept"), say what changes *for the user*, no
  internal jargon or ticket numbers, no trailing full stop. The first letter is capitalised in the
  changelog.

Good: `fix(compiler): chunk each file by its own event count`
Bad: `fix: handle edge case in _plan_chunks (#123)`

## Types

| Type | Changelog |
|---|---|
| `feat` | **Added** |
| `fix` | **Fixed** |
| `refactor`, `perf` | **Changed** |
| `docs`, `chore`, `ci`, `build`, `test`, `style`, `release`, `revert`, `deps` | hidden (`deps` is the prefix Dependabot uses) |

A release needs at least one visible entry since the last tag. A package with only hidden commits
does not release and stays at its old version.

## Trailer: `Changelog:`

The types cannot express Deprecated, Removed or Security. Add a trailer to the commit body:

```
fix(cli): drop the --legacy flag

Changelog: removed
```

| Value | Effect |
|---|---|
| `deprecated` | entry goes under **Deprecated**, whatever the type |
| `removed` | entry goes under **Removed** |
| `security` | entry goes under **Security** |
| `skip` | commit is hidden (an internal `feat`/`fix` that users never see) |

Any other value is rejected. Section order in the changelog follows keepachangelog: Added, Changed,
Deprecated, Removed, Fixed, Security.

## Merge style

Pull requests land as merge commits. Merge commits are ignored by the changelog and the check; the
individual commits count, so every commit in a pull request must follow the convention.
`fixup!` and `squash!` commits pass the local hook but fail CI: fold them before the pull request.

## Enforcement

- Locally: the `fasthep-commit-msg` hook in `.pre-commit-config.yaml` (see the README).
- In CI: the reusable `commit-check.yml` checks every commit in the pull request range.
- At tag time: `changelog-contract.yml` stops the publish if the tag has no changelog section.
