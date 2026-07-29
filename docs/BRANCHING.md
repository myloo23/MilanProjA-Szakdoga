# Branching Strategy

Trunk-based development. One long-lived branch, short-lived branches off it,
everything merged through a pull request. This is the single source of truth;
`PLAN.md` and `DEVELOPMENT.md` link here.

```
main (protected, always deployable, only branch that publishes an image)
 ├── feat/ansible-scaffold      ← lives < 2 days
 ├── fix/echo-invalid-json
 └── chore/sprint1-cleanup
```

## The rules

1. **`main` is always deployable.** Never commit to it directly — no exceptions,
   including under demo pressure.
2. **Branch from `main`, name it `<type>/<kebab-description>`.** Types are the
   Conventional Commit types: `feat`, `fix`, `docs`, `ci`, `build`, `refactor`,
   `test`, `chore`, `perf`.
3. **One branch, one story.** If it lives longer than about two days, the story
   was too big — split it.
4. **Rebase onto `main` before opening the pull request.** No merge commits from
   `main` into a feature branch.
5. **Squash merge, then delete the branch.** One story becomes one commit on
   `main`, which makes `git log` readable and a revert trivial.
6. **Only `main` publishes.** Feature branches build, test and scan the image;
   the push to the registry is gated on `refs/heads/main`.

Tags: annotated `v0.1.0`, `v0.2.0` at each milestone.

## Why not GitFlow

`develop`, `release/*` and `hotfix/*` exist to coordinate multiple teams shipping
versioned releases on separate cadences. One person, one environment, continuous
deployment — GitFlow would be cargo-culting. Trunk-based is the correct model for
a CD pipeline, and that trade-off is worth being able to explain out loud.

## Branch protection on `main`

Configure in Gitea → repository **Settings → Branches → Add rule** for `main`
(the GitHub mirror equivalent is a ruleset with the same boxes ticked):

| Setting | Value |
|---|---|
| Enable branch protection | on |
| Require pull request before merge | on |
| Require status checks to pass | `build-test-push` |
| Require branches to be up to date | on |
| Block force push | on |
| Block deletion | on |
| Allowed merge style | squash only |

Add `hadolint` and `ansible-lint` to the required checks when they land in
Sprint 2.

## The everyday loop

```bash
git checkout main && git pull
git checkout -b feat/short-description

# ... work, in small commits ...
git add <specific files>
git commit -m "feat(cd): add deploy_app role skeleton"

git fetch origin && git rebase origin/main
git push -u origin feat/short-description
gh pr create --fill
```

Before requesting review, read your own diff in the web UI and leave at least one
comment explaining a non-obvious decision. The pull request is where reasoning
gets recorded — that is why it exists even when working solo.
