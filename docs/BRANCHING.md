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

## Where the repository lives

The self-hosted Gitea instance is the origin — it is where pull requests are
opened, where the checks run and where `main` is protected. GitHub is a backup
remote, pushed to manually:

```bash
git remote -v
# origin  http://localhost:3000/milan/Milan-ProjectA.git   ← authoritative
# github  https://github.com/tcsdevopsintern/Milan-ProjectA.git  ← backup

git push github main    # whenever you want the off-machine copy current
```

This used to be the other way round, with Gitea as a pull mirror of GitHub. That
split the pipeline in half: pull requests lived on GitHub where no checks ran,
and the checks ran in Gitea where no pull request ever existed. Branch protection
could not gate anything, and deploys fired on the mirror's sync timer instead of
on merge. Making Gitea authoritative is what turns the rest of this document from
a description into a rule.

## Branch protection on `main`

Configured in Gitea → repository **Settings → Branches → Add rule** for `main`:

| Setting | Value |
|---|---|
| Protected branch name pattern | `main` |
| Push | Disable Push |
| Force push | Disable Force Push |
| Required approvals | `0` |
| Enable status check | on, pattern `Pipeline / build-test-push*` |
| Block merge if pull request is outdated | on |
| Administrators must follow branch protection rules | on |

And in **Settings → Pull Requests**: only *Create squash commit* enabled, set as
the default.

Three of those are easy to get wrong:

- **Required approvals stays at `0`.** Gitea does not count your own approval on
  your own pull request, so a solo developer who sets `1` can never merge again.
  The review discipline comes from reading your own diff, not from a counter.
- **The status check pattern ends in `*`.** The context is
  `Pipeline / build-test-push (push)` or `(pull_request)` depending on the event;
  an exact string silently matches neither on a pull request.
- **Never require `Pipeline / deploy`.** It only runs on `main`, so requiring it
  would block every merge permanently.

Add `hadolint` and `ansible-lint` to the pattern list when they land.

## The everyday loop

```bash
git checkout main && git pull
git checkout -b feat/short-description

# ... work, in small commits ...
git add <specific files>
git commit -m "feat(cd): add deploy_app role skeleton"

git fetch origin && git rebase origin/main
git push -u origin feat/short-description
```

Then open the pull request in Gitea — the push output prints a direct link, or go
to the repository and use the banner on the branch. There is no `gh` equivalent
here: that is GitHub's CLI, and origin is Gitea now. `tea` is the Gitea CLI if
the browser step ever becomes annoying.

Before requesting review, read your own diff in the web UI and leave at least one
comment explaining a non-obvious decision. The pull request is where reasoning
gets recorded — that is why it exists even when working solo.
