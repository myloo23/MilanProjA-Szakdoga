# Development Guide

Local setup, day-to-day commands, the CI platform, and the Git workflow.

---

## 1. Fresh clone to running app

```bash
git clone https://github.com/tcsdevopsintern/Milan-ProjectA.git
cd Milan-ProjectA

python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest && ruff check .

flask --app app/app.py run          # dev server, :5000
# or the production container:
docker build -t flaskapp:dev . && docker run -p 8000:8000 flaskapp:dev
curl localhost:8000/health
```

Both requirements files are hash-locked, so a laptop and CI install identical
versions. The CI platform (Gitea, runner, registry) is separate — [section 5](#5-platform-stack).

---

## 2. Dependencies

```bash
pip install -r requirements.txt        # runtime only — mirrors the image
pip install -r requirements-dev.txt    # + pytest, pytest-cov, ruff, pip-tools
```

To add or change one:

```bash
# edit requirements.in (runtime) or requirements-dev.in (tooling), then:
pip-compile --allow-unsafe --generate-hashes --strip-extras \
  --output-file=requirements.txt requirements.in
pip-compile --allow-unsafe --generate-hashes --strip-extras \
  --output-file=requirements-dev.txt requirements-dev.in
pip install -r requirements-dev.txt
```

**Recompile both, in the same commit — even when you only touched one `.in`
file.** `requirements-dev.in` starts with `-r requirements.in`, so the dev lock
is meant to be the runtime lock plus tooling. Compile one without the other and
the two resolve at different times: that is exactly how the image came to ship
`gunicorn 23.0.0` while CI installed `26.0.0`. Runtime dependencies are now
pinned in `requirements.in` rather than left floating, which is what makes the
two locks agree.

**Use these flags, not a shortened version.** `--allow-unsafe` is what pins
`pip`, `setuptools` and `wheel` in the dev lock; drop it and the next compile
silently removes them.

**Never hand-edit the `.txt` files** — they are generated. The hashes make
installs reproducible and tamper-evident; the Dockerfile enforces them with
`--require-hashes`.

---

## 3. Run, test, lint

```bash
flask --app app/app.py run --debug                              # :5000, auto-reload
gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 app.app:app # exactly what the image runs

pytest                    # pytest --cov=app for coverage
ruff check . --fix
```

CI runs the same commands plus `--cov-fail-under=80`.

Endpoints:

```bash
BASE=localhost:8000
curl $BASE/ ; curl $BASE/health ; curl $BASE/ready
curl -X POST $BASE/echo -H 'Content-Type: application/json' -d '{"hi":"there"}'
curl -X POST $BASE/echo -H 'Content-Type: application/json' -d '{"broken'   # -> 400
```

That last one is the deliberate error path the observability demo needs.

---

## 4. Docker

```bash
docker build -t flaskapp:dev .
docker run -d --name flaskapp -p 8000:8000 flaskapp:dev
docker logs -f flaskapp
docker stop flaskapp && docker rm flaskapp
docker image prune                    # multi-stage builds leave dangling images
```

**Working directory gotcha:** the app is at `app/app.py`, `WORKDIR` is `/app`, so
the import path is `app.app:app` — a package path, not a file path. Pointing
`WORKDIR` at the inner `app/` directory breaks it with
`Failed to find Flask application or factory in module 'app'`.

---

## 5. Platform stack

| Service | Container | Purpose |
|---|---|---|
| Gitea | `projecta-gitea` | Git server + CI coordinator, `localhost:3000` |
| act_runner | `projecta-act-runner` | Runs the workflows, `capacity: 1` |
| Registry | `projecta-registry` | Stores images, `localhost:5001` |

**Addressing — read this before debugging a failed push or smoke test.** Between
containers: `gitea:3000`, `registry:5000`. From the host: `localhost:3000`,
`localhost:5001`. Inside a container `localhost` is *that container* — the single
most common source of confusing failures here.

```bash
cp platform/.env.example platform/.env
# set GITEA_RUNNER_REGISTRATION_TOKEN — Gitea → Site Administration → Actions → Runners

docker compose --env-file platform/.env -f platform/compose.yaml up -d
docker compose --env-file platform/.env -f platform/compose.yaml down

curl http://localhost:3000/api/healthz   # Gitea
curl http://localhost:5001/v2/           # Registry
```

`platform/.env` is gitignored — it holds a registration token and must never be
committed. Data lives in the named volumes `projecta-{gitea,runner,registry}-data`,
so containers can be recreated safely. Adding `-v` to `down` **deletes them** —
only for testing the clean-machine path.

---

## 6. CI pipeline

`.gitea/workflows/ci.yml`, triggered on **push** to `main`, `release/*`,
`feature/*` and `hotfix/*`. There is no `pull_request` trigger: pull requests
live on GitHub, so that event would never fire here.

`build-test-push`:

1. Checkout, then decide whether this ref ships an artifact
2. Python 3.12 with a pip cache, deps with `--require-hashes`
3. `ruff check .`
4. `hadolint` on the Dockerfile
5. `pytest` with coverage, failing under 80%
6. `ansible-lint` at the `production` profile, over the playbooks and the role
7. Build `localhost:5001/projecta-flask:<git-sha>`
8. Wait for the container's own `HEALTHCHECK` to report healthy, bounded at 30s
9. `curl` the app across `projecta-platform` — proves it is *reachable*, which a
   healthcheck probing its own localhost cannot
10. Trivy, failing on HIGH or CRITICAL
11. Push to the registry — **only if this ref ships**

Steps 1–5 run against dependencies the job already has; step 6 is the first that
pays for a download, which is why it sits there rather than beside `ruff`. It
still precedes the build, because a playbook that cannot lint cannot deploy the
image the later steps produce.

`deploy` runs after it, on the same condition. It installs pinned `ansible-core`
and collections, then runs `playbooks/deploy.yml` with `app_version=<sha>`. It
never builds anything.

**Which refs ship:** `main` and `release/*` push and deploy. `feature/*` and
`hotfix/*` build, test and scan, then stop. The decision is one shell `case` on
the ref, computed once and consumed by both the push step and the deploy job.

Two jobs in one workflow, not two workflows: the runner has `capacity: 1`, so
independently triggered workflows could be scheduled in either order and CD would
wait for an image CI had not pushed yet. `needs:` removes the question.

The deploy job passes `deploy_app_smoke_vantage=network` — its steps run in a
container, so `localhost` there is the job container, not the Docker host.

---

## 7. Ansible (CD)

`ansible.cfg` is only read from the current directory, so **run everything from
inside `ansible/`**.

```bash
pip install -r ansible/requirements-ansible.txt   # same ansible-core as CI
cd ansible
ansible-galaxy collection install -r requirements.yml
```

### Lint before you run

```bash
pip install -r ansible/requirements-lint.txt      # inherits the ansible-core pin
cd ansible
ansible-lint .
```

The strictness lives in `ansible/.ansible-lint` (`profile: production`), not in
a flag, so this command and the CI step cannot disagree about what passing
means. `requirements-lint.txt` includes `requirements-ansible.txt` rather than
repeating its pin — one `ansible-core` version, or CI eventually lints against
an Ansible the deploy does not use.

Run it with the collection installed. `syntax-check` resolves every module it
sees, and without `community.docker` it reports `unknown-module` on tasks that
are correct.

### Verify the target first

```bash
ansible-playbook playbooks/ping.yml
```

Green means: host reachable, Docker socket answers, collection installed,
`projecta-platform` exists. Run it before debugging anything further up — it
separates "my playbook is wrong" from "my environment is wrong" in five seconds.

### The variables that matter

| Variable | Set in | Why |
|---|---|---|
| `docker_host` | `group_vars/local_docker.yml` | Which daemon to drive. A remote target is `tcp://host:2376` plus TLS vars, with no role change |
| `app_version` | **passed by CD only**, `-e app_version=<sha>` | Deliberately has no default, so a deploy cannot silently ship an untested artifact |
| `deploy_app_smoke_vantage` | role default `host`; CD passes `network` | Where the smoke test looks from — published port vs container name |

### Deploy, roll back, dry run

```bash
ansible-playbook playbooks/deploy.yml -e app_version=<git-sha>
ansible-playbook playbooks/deploy.yml -e app_version=<previous-sha>   # rollback
ansible-playbook playbooks/deploy.yml -e app_version=<sha> --check --diff
```

Deploy pulls that exact image, runs it with limits and log rotation, then checks
`/health`, `/ready` and both `/echo` paths. Any failure fails the play — there is
no "succeeded with warnings".

Run it twice with the same SHA and the second reports `changed=0`. Verified
2026-07-31 against `fbc1254e`: `ok=11 changed=0`, with every smoke check re-run
and passing. Worth knowing when you are unsure whether a deploy landed — running
it again is free.

**Rollback is the same command with an earlier SHA.** No separate path to keep
working, which is why it can be trusted in an incident. A failed deploy prints
this command with the previous SHA already filled in.

Find SHAs with `git log --oneline main` or:

```bash
curl -s localhost:5001/v2/projecta-flask/tags/list
```

---

## 8. Git workflow

Two remotes. `origin` is GitHub (review, protection), `gitea` is localhost (the
pipeline). Full rules in [`BRANCHING.md`](BRANCHING.md).

```bash
git checkout release/sprint2 && git pull origin release/sprint2
git checkout -b feature/sprint-2-short-description

git add <specific files>          # not `git add -A` — review what you stage
git commit -m "feat(app): add /metrics endpoint"
git fetch origin && git rebase origin/release/sprint2

git push gitea feature/sprint-2-short-description     # 1. prove it, wait for green
git push -u origin feature/sprint-2-short-description # 2. then ask for review
```

Then open the pull request on GitHub into `release/sprint2` and **paste the Gitea
run result into the description** — there are no status checks on GitHub, so that
is the only evidence a reviewer has.

Commit types: `feat`, `fix`, `docs`, `ci`, `build`, `refactor`, `test`, `chore`,
`perf`. Scopes: `app`, `ci`, `cd`, `ansible`, `docker`, `obs`, `docs`.

---

## Related docs

| Document | Contents |
|---|---|
| [`../README.md`](../README.md) | Overview, architecture, status |
| [`PLAN.md`](PLAN.md) | Roadmap, sprints, open work, risks |
| [`BRANCHING.md`](BRANCHING.md) | Branches, merge policy, protection |
| [`adr/`](adr/) | Why the big decisions were made |
| [`ProjectA.md`](ProjectA.md) | Original assignment brief |
