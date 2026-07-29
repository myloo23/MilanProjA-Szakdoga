# Development Guide

Everything needed to work on Project A: local setup, day-to-day commands, the
self-hosted CI platform, and the Git workflow.

---

## 1. From a fresh clone to a running app

The fastest path from `git clone` to a working app. This is also the sequence to
test on a clean machine before a demo.

```bash
git clone https://github.com/tcsdevopsintern/Milan-ProjectA.git
cd Milan-ProjectA

# 1. Python environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Sanity check
pytest
ruff check .

# 3. Run the app locally
flask --app app/app.py run
# -> http://127.0.0.1:5000

# 4. Or build and run the production container instead
docker build -t flaskapp:dev .
docker run -p 8000:8000 flaskapp:dev
curl localhost:8000/health
```

Both requirements files are hash-locked, so `pip install` reproduces the exact same
dependency versions every time — no drift between a laptop and CI.

The local CI platform (Gitea, runner, registry) is separate; see
[section 5](#5-platform-stack).

---

## 2. Python environment and dependencies

### Virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate      # deactivate with: deactivate
```

Keeps dependencies isolated from the system Python.

### Install

```bash
pip install -r requirements.txt        # runtime only — mirrors the Docker image
pip install -r requirements-dev.txt    # runtime + pytest, pytest-cov, ruff, pip-tools
```

`requirements-dev.in` starts with `-r requirements.in`, so the dev file already
includes everything in the runtime file. One install gives you the full toolset.

### Add or update a dependency

```bash
# 1. Edit requirements.in (runtime) or requirements-dev.in (dev tooling)
# 2. Recompile the locked, hash-pinned files
pip-compile --generate-hashes --strip-extras requirements.in
pip-compile --generate-hashes --strip-extras requirements-dev.in

# 3. Re-install
pip install -r requirements-dev.txt
```

Never hand-edit `requirements.txt` or `requirements-dev.txt` — they are generated.
`pip-compile` resolves versions and pins hashes so installs are reproducible and
tamper-evident. The Dockerfile enforces this at build time with `--require-hashes`.

---

## 3. Running, testing, linting

### Flask dev server

```bash
flask --app app/app.py run
flask --app app/app.py run --debug   # auto-reload + interactive debugger
```

Fastest inner loop. Serves on port 5000.

### Gunicorn — matches production

```bash
gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 app.app:app
```

This is exactly what the Dockerfile runs. Use it to reproduce the production
process model locally.

### Exercise the endpoints

```bash
BASE=localhost:8000          # or :5000 when using the Flask dev server

curl $BASE/
curl $BASE/health
curl $BASE/ready
curl -X POST $BASE/echo -H 'Content-Type: application/json' -d '{"hi":"there"}'
curl -X POST $BASE/echo -H 'Content-Type: application/json' -d '{"broken'   # -> 400
```

That last one is the deliberate error path the observability demo depends on.

### Tests and lint

```bash
pytest                    # run the suite
pytest -v                 # one line per test
pytest --cov=app          # with a coverage report

ruff check .              # lint
ruff check . --fix        # auto-fix what is safely fixable
ruff format .             # format
```

Run `pytest` and `ruff check .` before every push — CI runs the same commands, so
catching failures locally saves a round trip. CI additionally enforces
`--cov-fail-under=80`.

---

## 4. Docker

### Build and run

```bash
docker build -t flaskapp:dev .
docker run --name flaskapp -p 8000:8000 flaskapp:dev
docker run -d --name flaskapp -p 8000:8000 flaskapp:dev   # detached
```

The image is multi-stage: a builder installs hash-verified wheels into a prefix, and
the runtime stage copies only those wheels onto a digest-pinned `python:3.12-slim`
base. It runs as the non-root user `appuser` (UID 10001) and has a `HEALTHCHECK`
polling `/health`.

### Manage containers

```bash
docker ps                       # list running containers
docker logs -f flaskapp         # follow logs — Gunicorn writes access and error logs to stdout
docker exec -it flaskapp sh     # shell in for debugging
docker stop flaskapp
docker rm flaskapp
```

### Clean up

```bash
docker image prune              # remove dangling images
docker system prune             # remove all unused containers, images, networks
```

Multi-stage rebuilds leave dangling images behind. Prune periodically so build
output stays readable and the disk does not fill up.

### Note on the container working directory

The application lives at `app/app.py` and the container's working directory is
`/app`, so the app is imported as `app.app:app` — the Python package path, not a
file path. Setting `WORKDIR` to the inner `app/` directory breaks the import and
produces:

```text
Error: Failed to find Flask application or factory in module 'app'
```

Keep `WORKDIR /app` and let the module path do the work.

---

## 5. Platform stack

The self-hosted CI platform lives in `platform/`, separate from the application.

| Service | Container | Purpose |
|---------|-----------|---------|
| Gitea | `projecta-gitea` | Git server and CI coordinator (web UI on port 3000) |
| act_runner | `projecta-act-runner` | Executes Gitea Actions workflows |
| Registry | `projecta-registry` | Stores built Docker images (host port 5001) |

All three join the `projecta-platform` Docker network and resolve each other by
service name.

### Network addressing — read this before debugging a failed push

Inside the network, containers reach each other by service name and internal port:
`gitea:3000`, `registry:5000`. From the host, the same services are published on
`localhost:3000` and `localhost:5001`.

Never use `localhost` between containers — inside a container `localhost` is that
container itself. This mismatch is the most common source of confusing push and
pull failures in this project.

### First-time setup

```bash
cp platform/.env.example platform/.env
# Then edit platform/.env and set GITEA_RUNNER_REGISTRATION_TOKEN.
# Get the token from: Gitea -> Site Administration -> Actions -> Runners -> Create
```

`platform/.env` is gitignored on purpose — it holds a registration token and must
never be committed.

### Start and stop

```bash
docker compose --env-file platform/.env -f platform/compose.yaml up -d
docker compose --env-file platform/.env -f platform/compose.yaml down
```

`down` stops the services without deleting data.

### Verify

```bash
curl http://localhost:3000/api/healthz   # Gitea
curl http://localhost:5001/v2/           # Registry
```

### Data persistence

Data lives in named Docker volumes, so containers can be recreated safely:

- `projecta-gitea-data`
- `projecta-runner-data`
- `projecta-registry-data`

### Reset — destructive

```bash
docker compose --env-file platform/.env -f platform/compose.yaml down -v
```

`-v` deletes those volumes: Gitea's database, repositories and registry contents are
all wiped. Use only when deliberately testing the clean-machine setup path.

---

## 6. CI pipeline

`.gitea/workflows/ci.yml` runs on every push and pull request:

1. Check out the repository
2. Set up Python 3.12 with a pip cache
3. Install dev dependencies with `--require-hashes`
4. `ruff check .`
5. `pytest` with coverage, failing under 80%
6. Build the image, tagged `localhost:5001/projecta-flask:<git-sha>`
7. Run the container on `projecta-platform` and curl `/health` — a container smoke test
8. Scan the image with Trivy, failing on HIGH or CRITICAL
9. Clean up the test container
10. Push the image to the local registry

Every stage above is runnable locally with the commands in this document, which is
the point — a stage that only works in CI cannot be debugged.

---

## 7. Ansible (CD)

Everything Ansible lives in `ansible/`. `ansible.cfg` is only read from the
current working directory, so **run every command from inside `ansible/`**.

```
ansible/
├── ansible.cfg                        # inventory path, diff always on
├── requirements.yml                   # community.docker collection
├── inventory/
│   ├── hosts.yml                      # the local_docker group
│   └── group_vars/local_docker.yml    # docker_host, registry, app variables
├── playbooks/
│   └── ping.yml                       # skeleton check
└── roles/                             # deploy_app lands here next
```

### First-time setup

```bash
cd ansible
ansible-galaxy collection install -r requirements.yml
```

### Verify the target

```bash
cd ansible
ansible-playbook playbooks/ping.yml
```

Green means: the host is reachable, the Docker socket answers, the
`community.docker` collection is installed, and the `projecta-platform` network
exists. Run this before debugging anything further up the stack — it separates
"my playbook is wrong" from "my environment is wrong" in five seconds.

```bash
ansible-playbook playbooks/ping.yml --skip-tags docker   # connectivity only
ansible-inventory --graph --vars                          # what the host resolves to
```

### The two variables that matter

| Variable | Set in | Why |
|---|---|---|
| `docker_host` | `group_vars/local_docker.yml` | Which Docker daemon to drive. `unix:///var/run/docker.sock` today; a remote target is `tcp://host:2376` plus TLS vars and no role change |
| `app_version` | **passed by CD only** — `-e app_version=<git-sha>` | The exact image CI built. Deliberately has no default, so a deploy cannot silently ship an untested artifact |

`registry_endpoint` is the other one to watch: `localhost:5001` from the host,
`registry:5000` from inside a container on `projecta-platform`. See
[section 5](#5-platform-stack).

### Dry run

```bash
ansible-playbook playbooks/deploy.yml -e app_version=<sha> --check --diff
```

`diff` is on by default in `ansible.cfg`, so `--check` shows what a run would
change without changing it.

---

## 8. Git workflow

Trunk-based development, short-lived branches off `main`, Conventional Commits,
squash merge via pull request. Full rules and branch protection settings in
[`BRANCHING.md`](BRANCHING.md).

```bash
git checkout main && git pull
git checkout -b feat/short-description        # <type>/<kebab-description>

# ... make changes ...

git add <specific files>                       # avoid `git add -A` — review what you stage
git commit -m "feat(app): add /metrics endpoint"
git rebase main                                # keep the branch current before opening a PR
git push -u origin feat/short-description
gh pr create --fill
```

Commit types: `feat`, `fix`, `docs`, `ci`, `build`, `refactor`, `test`, `chore`,
`perf`. Scopes: `app`, `ci`, `cd`, `ansible`, `docker`, `obs`, `docs`.

Branches older than about two days usually mean the change was too big — split it.
Squash merging keeps `main` at one commit per story, which makes `git log` readable
and reverts trivial.

---

## Related docs

| Document | Contents |
|----------|----------|
| [`../README.md`](../README.md) | Project overview, architecture, status |
| [`PLAN.md`](PLAN.md) | Roadmap, sprints, TODO, risks, conventions |
| [`BRANCHING.md`](BRANCHING.md) | Branching strategy and branch protection settings |
| [`adr/`](adr/) | Architecture decision records |
| [`ProjectA.md`](ProjectA.md) | Original assignment brief |
