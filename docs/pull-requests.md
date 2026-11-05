# Writing pull requests

A pull request body should be readable in two minutes: about 300 words above any collapsed detail. The default
template in `.github/PULL_REQUEST_TEMPLATE.md` has the shape; this page gives the budgets and says where the
rest goes. The header line is `Base: <branch> · Depends on: #N · Refs: <issue>`; `Depends on` only for a stacked PR.

| Section | Budget | What |
|---|---|---|
| Summary | about 100 words and one visual | What changes and why. One tree, call tree or diff, not all three. |
| Evidence | about 100 words | Before and after as failing-then-passing test names and the one assertion that matters; the suite line. |
| Merge Danger | about 60 words | Door (two-way or one-way) and blast radius. |
| AI assistance | four one-line bullets | Generated, Reviewed, Decision, Limits. |

## Where the rest goes

- **What the issue already says:** link it, do not restate it. The question, the contract and the
  motivating case live in the issue; the PR says what this change does, its evidence and its risk.
- **Public names, known limitations, long test lists:** one collapsed block at the end, summary "Details".
- **Follow-ups:** an issue, linked. Do not list them in the PR body, beyond the one or two a reviewer must know.
- **Exact tables and schemas:** the docs page the PR adds, linked.
- **In a stack:** say where the PR sits (`Base`, `Depends on`) and do not re-explain the design of the parent;
  link its PR.

## For agents, and anyone drafting with one

- Write the body after the user has pushed, and open the PR ready for review unless asked for a draft.
- Do not repeat the issue. Say what this PR does; link the issue for the why and the contract.
- Count: over about 350 visible words, cut or move detail into the collapsed block.
- Evidence is something that ran, with its result, not a description of intent.
- The AI assistance bullets are one line each and name the model. They keep the four things the
  contribution guide asks for: what was generated, what was reviewed, the design decisions, the limits.
- Start from the skeleton in `.github/PULL_REQUEST_TEMPLATE.md` of the `.github` repository (for example
  `gh api repos/FAST-HEP/.github/contents/.github/PULL_REQUEST_TEMPLATE.md --jq .content | base64 -d`) and pass
  the result with `gh pr create --body-file`.

## Example

The body of fasthep-flow#117 had 607 words. Rewritten, it has 266 visible words (445 in all): it links
fasthep-flow#105 for the question and the contract instead of repeating them, and keeps the public names, the
layout and the limitations in the collapsed block.
