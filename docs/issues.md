# Writing issues

An issue should be readable on one screen: about 200 words above any collapsed detail. The default template
in `.github/ISSUE_TEMPLATE/task.md` has the shape; this page says how to fill it.

## The shape

- **Lead paragraph, no heading.** The problem or goal in two or three sentences, with one concrete number
  or example (for example "all 34 reported changes were provenance, yet the command exited 1").
- **`## What`.** The change or the question being answered, as 3 to 5 bullets.
- **`## Done when`.** 3 to 5 outcomes someone can check. Outcomes, not an inventory of every test.
- **`## Related`.** Linked issues and PRs, the delivery plan (for example stacked PRs), and
  `Depends on: owner/repo#N` for a real prerequisite.

An epic is a goal, a checklist with one line per item, and a line on what it does not cover.

## Where the rest goes

- **Requirements, design notes, long test lists:** one collapsed block at the end, summary
  "Requirements and tests". Nothing is lost; the page stays short.
- **A design that needs its own page:** a docs page in the repository, linked from the issue. The first
  PR can add it.
- **Never** link local notes or private paths. Issues are public.

## For agents, and anyone drafting with one

- Draft in this shape, then count: over about 250 visible words, cut or move detail into the collapsed block.
- Say the outcome, not the investigation. Do not restate the title or paste an implementation plan.
- Prefer a number or an example to an adjective.
- Keep the issue current: edit the body when the design changes instead of adding a pile of comments.
- If an agent drafted it, end with the footer in the template, naming the model. The author still reviews it.
- File with `gh issue create --template Task --title "..."` (it starts from the template), or with
  `--body-file`.

## Example

fasthep-flow#105 had 617 words in seven sections. Rewritten, it has 222 visible words under What, Done when
and Related, with the original requirements kept verbatim in the collapsed block.

A PR template follows once the pull request for fasthep-flow#105 exists.
