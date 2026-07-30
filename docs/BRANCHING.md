# Branching Strategy

Two protected branches and short-lived work branches, reviewed on GitHub and
built on Gitea. This is the single source of truth; `PLAN.md` and
`DEVELOPMENT.md` link here.

```
main (protected)                    validated sprint work only
 └── release/sprint2 (protected)    the sprint checkpoint — what gets demonstrated
      ├── feature/sprint-2-...      lives < 2 days
      └── hotfix/...                same rules, different intent
```

## The two forges, and why there are two

| | GitHub | Gitea (`localhost:3000`) |
|---|---|---|
| Role | **who may merge** — review, approval, protection | **does it work** — build, test, scan, deploy |
| Holds | `main`, `release/sprint2` | every branch that needs a pipeline run |
| Pull requests | yes, this is where they live | never again |
| Runner | none | `act_runner`, capacity 1 |

Each forge enforces exactly one thing. Duplicating a rule across both would
mean two mechanisms for one intent, and two mechanisms drift — after which
nobody can say which is authoritative.

```bash
git remote -v
# origin  https://github.com/tcsdevopsintern/Milan-ProjectA.git   ← source of truth
# gitea   http://localhost:3000/milan/Milan-ProjectA.git          ← runs the pipeline
```

**There are no status checks on the GitHub pull request.** No runner lives
there, and requiring a check that can never arrive would block every merge
permanently. The proof that a branch is green lives in Gitea — so paste the
Gitea run link into the pull request description. A reviewer cannot approve
what they cannot see was tested.

## The rules

1. **Never commit to `main` or `release/sprint2`.** Both are protected on
   GitHub; work reaches them only through a reviewed pull request.
2. **Branch from `release/sprint2`**, name it `feature/sprint-2-<kebab>` or
   `hotfix/<kebab>`.
3. **One branch, one story.** Longer than about two days means the story was
   too big — split it.
4. **Push to `gitea` first, and wait for green.** Opening a pull request on a
   branch you have not proven wastes a reviewer's attention, and their
   attention is the scarcest thing in this process.
5. **Then push to `origin` and open the pull request into `release/sprint2`.**
   Chase the approvers; a pull request nobody looks at is not progress.
6. **`feature/*` → `release/sprint2`: squash merge, then delete the branch.**
   One story, one commit on the integration branch.
7. **`release/sprint2` → `main`: merge commit, never squash.** This one is not
   a matter of taste. A squash rewrites the sprint into a single new commit
   that `main` has and `release/sprint2` does not, so the two branches share no
   history from that point on and every later merge between them replays
   changes git already applied. An integration branch that is squashed into
   `main` is an integration branch you have to delete and recreate. A merge
   commit keeps both branches on the same history.
8. **That merge happens only when the mentors validate the sprint.** It is the
   sprint boundary, not a routine event.

Both merge strategies must be enabled in GitHub → Settings → General → Pull
Requests, because the repository needs squash for one direction and merge
commits for the other.

## Review is part of the work, not an interruption

Colleagues review pull requests into `release/sprint2`; mentors approve
`release/sprint2` → `main`. Reviewing is reciprocal — approving without reading
costs you the reviewer next time, and a pull request left open for days without
a comment is the same failure seen from the other side. Budget time for other
people's branches, leave a comment that shows you read the diff, and chase your
own approvers rather than waiting to be noticed.

Tags: annotated `v0.1.0`, `v0.2.0` at each milestone.

## Why an integration branch and not pure trunk-based

Trunk-based development assumes the people who review your code and the people
who run it are the same group, working on the same cadence. Here they are not:
the sprint is validated by mentors at a checkpoint, which is precisely what an
integration branch models. `release/sprint2` is the sprint made visible — it
either deploys or it does not, and that is the question the checkpoint asks.

The cost is real and worth naming: two protected branches means changes can sit
unmerged longer, and `main` and `release/sprint2` can diverge if the sprint runs
long. Trunk-based avoided that by having nowhere to diverge to.

## Which branches trigger what

| Branch | Build, lint, test, scan | Push to registry | Deploy |
|---|---|---|---|
| `feature/**`, `hotfix/**` | yes | no | no |
| `release/**` | yes | yes | yes |
| `main` | yes | yes | yes |

`release/*` deploys as well as `main` on purpose. It is the branch that gets
demonstrated, so it is the branch that has to be provably deployable. If CD ran
only on `main`, its first real execution would be the end-of-sprint merge — the
most expensive possible moment to discover a problem.

The gate is a shell `case` on the ref in `ci.yml`, not an `if:` expression,
because prefix matching would need `startsWith()` and its behaviour under
`act_runner` is not something to bet a release gate on.

## Branch protection

**GitHub — `main` and `release/sprint2`**, Settings → Branches:

| Setting | Value |
|---|---|
| Require a pull request before merging | on |
| Require approvals | 1 |
| Require review from Code Owners | on |
| Do not allow bypassing the above settings | on |
| Allow force pushes | off |
| Require status checks | **off** — no runner exists on GitHub |

Reviewers come from `CODEOWNERS`, which GitHub reads **from the base branch of
the pull request**. That is what gives the two branches different review
circles from one filename: the copy on `main` names the mentors, the copy on
`release/sprint2` also names the Project A team. Listed owners must have write
access to the repository or GitHub skips them silently.

**Gitea — `main`**: push whitelist includes `milan`, force push stays off.

That whitelist looks like a weakened rule and is not. Gitea's `main` is now a
downstream copy of GitHub's, and it has to be able to follow it. With force
push disabled it can only fast-forward — so it can track GitHub, never diverge
from it or overwrite it. The rule that actually matters, that changes are
reviewed before they land, is enforced on GitHub where authorship happens.

## The everyday loop

```bash
git checkout release/sprint2 && git pull origin release/sprint2
git checkout -b feature/sprint-2-short-description

# ... work, in small commits ...
git add <specific files>
git commit -m "feat(cd): add deploy_app role skeleton"

git fetch origin && git rebase origin/release/sprint2

git push gitea feature/sprint-2-short-description    # 1. prove it
# wait for the Gitea run to go green

git push -u origin feature/sprint-2-short-description # 2. then ask for review
```

Then open the pull request on GitHub into `release/sprint2`, paste the Gitea
run link into the description, and request the reviewers if CODEOWNERS has not
already done it.

Before requesting review, read your own diff and leave at least one comment
explaining a non-obvious decision. The pull request is where reasoning gets
recorded — that is why it exists even when the change is small.
