# ADR-0004: GitHub owns review, Gitea owns execution

## Status

Accepted — 2026-07-30. Supersedes the "Gitea is the origin" part of
[ADR-0001](0001-self-hosted-gitea-actions.md); the rest of ADR-0001 stands.

## Context

Pull requests have to be reviewed by mentors and colleagues. Gitea runs on
`localhost:3000` — nobody else can reach it, so no review can happen there.
GitHub is reachable but has no runner, so no pipeline can run there.

Neither forge can do both jobs.

## Decision

Split them by what each is actually able to do.

| | GitHub | Gitea |
|---|---|---|
| Owns | review, approval, branch protection | build, test, scan, deploy |
| Holds | `main`, `release/sprint2` | every branch that needs a run |
| Pull requests | yes | never |

Consequences of that split:

- **The repository is public.** On a private repository, branch protection and
  `CODEOWNERS` are unavailable on this plan, so neither could be enforced. The
  repository contains no secrets — `.env` is ignored and the full history was
  checked before the switch.
- **Triggers are push-based.** With no pull request in Gitea, a
  `pull_request:` trigger can never fire, and feature branches would get no CI
  at all.
- **No status checks on GitHub pull requests.** There is no runner to produce
  them, and requiring a check that cannot arrive would block every merge. The
  CI result is pasted into the pull request description instead.
- **`release/sprint2` is an integration branch.** Feature branches merge into
  it after review; it merges into `main` when the mentors validate the sprint.

## Consequences

**Positive**

- Each rule is enforced in exactly one place, so the two forges cannot drift.
- Review is a real gate: the merge button is blocked without an approval.
- The pipeline keeps running on owned infrastructure, so ADR-0001's ownership
  story survives intact.

**Negative / trade-offs**

- Two remotes to push to, and it is possible to open a pull request on code
  that was never built.
- The pipeline result is copied by hand into the pull request, which means it
  can be stale or wrong. A reviewer has to trust the author on that.
- The work is public. Nothing confidential can ever be committed.

## Alternatives considered

- **Keep Gitea as the origin.** Costs nothing to leave alone and makes review
  impossible, which was the requirement. Rejected.
- **Self-hosted GitHub Actions runner.** Would put checks on the pull request
  and remove the copy-paste evidence. Not rejected on merit — deferred, as the
  current split satisfies the requirement without a second runner to maintain.
- **Stay private, no enforcement, review by discipline.** Workable, and the
  fallback if the repository ever has to be private again. Rejected while
  public is allowed: a rule a tool enforces survives a tired Friday.
