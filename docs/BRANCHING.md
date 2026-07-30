# Branching

```
main (protected)                 validated sprint work only
 └── release/sprint2 (protected) the sprint checkpoint — what gets demonstrated
      ├── feature/sprint-2-...   lives < 2 days
      └── hotfix/...
```

## Two forges

| | GitHub (`origin`) | Gitea (`gitea`, localhost:3000) |
|---|---|---|
| Owns | review, approval, protection | build, test, scan, deploy |
| Pull requests | yes | never |

Why: see [ADR-0004](adr/0004-github-for-review-gitea-for-execution.md).

**No status checks on the GitHub pull request** — there is no runner there.
Paste the Gitea run result into the pull request description; it is the only
evidence a reviewer has.

## Rules

1. Never commit directly to `main` or `release/sprint2`.
2. Branch from `release/sprint2`: `feature/sprint-2-<kebab>` or `hotfix/<kebab>`.
3. One branch, one story. Longer than ~2 days means it was too big.
4. Push to `gitea` first and wait for green. Only then open the pull request.
5. Pull request goes into `release/sprint2`. Chase the approvers.
6. `feature/*` → `release/sprint2`: **squash merge**, then delete the branch.
7. `release/sprint2` → `main`: **merge commit, never squash.** A squash would put
   a commit on `main` that `release/sprint2` does not share, leaving the two with
   no common history and every later merge replaying old changes.
8. That merge happens only when the mentors validate the sprint.

Both merge strategies must stay enabled in GitHub → Settings → General.

## What triggers what

| Branch | Lint, test, scan | Push to registry | Deploy |
|---|---|---|---|
| `feature/**`, `hotfix/**` | yes | no | no |
| `release/**`, `main` | yes | yes | yes |

`release/*` deploys because it is the branch that gets demonstrated. If CD ran
only on `main`, its first real run would be the end-of-sprint merge.

The gate is a shell `case` on the ref in `ci.yml`, not an `if:` expression —
prefix matching would need `startsWith()`, unverified under `act_runner`.

## Protection

**GitHub** — one ruleset, `Active`, targets `main` and `release/*`, empty bypass list:

| Rule | |
|---|---|
| Require a pull request before merging | on, 1 approval |
| Require review from Code Owners | on |
| Restrict deletions · Block force pushes | on |
| Require linear history | **off** — it would block the merge commit into `main` |
| Require status checks | **off** — no runner on GitHub |

Reviewers come from `CODEOWNERS`, which GitHub reads **from the base branch**.
That is what gives `main` (mentors) and `release/sprint2` (mentors + team)
different review circles from one filename. Listed owners need write access or
GitHub skips them silently.

**Gitea** — `main`: push whitelist includes `milan`, force push off. Gitea's
`main` is a downstream copy of GitHub's and has to be able to follow it; with
force push disabled it can only fast-forward.

## Everyday loop

```bash
git checkout release/sprint2 && git pull origin release/sprint2
git checkout -b feature/sprint-2-short-description

# ... work, small commits ...
git fetch origin && git rebase origin/release/sprint2

git push gitea feature/sprint-2-short-description    # 1. prove it, wait for green
git push -u origin feature/sprint-2-short-description # 2. then ask for review
```

Then open the pull request on GitHub into `release/sprint2` and paste the Gitea
result in.

## Review etiquette

Colleagues review pull requests into `release/sprint2`; mentors approve
`release/sprint2` → `main`. Reviewing is reciprocal — approving without reading
costs you the reviewer next time, and leaving a pull request open for days is
the same failure from the other side.
