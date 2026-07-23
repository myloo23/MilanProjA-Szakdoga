# Dev Cheat Sheet

Command reference for working on Project A. Every command includes what it does and why you'd reach for it.

---

## 0. Rebuilding from a fresh clone

The fastest path from `git clone` to a running app. This is also the sequence to test on a clean machine before a demo.

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

# 4. Or build/run the production container instead
docker build -t flaskapp:dev .
docker run -p 8000:8000 flaskapp:dev
curl localhost:8000/health
```

Requirements files are hash-locked (`requirements.txt`, `requirements-dev.txt`), so `pip install` reproduces the exact same dependency versions every time — no "works on my machine" drift between your laptop and CI.

If you also need the local CI/CD platform (Gitea + runner + registry), see [section 4](#4-platform-stack-gitea--registry--runner).

---

## 1. Python environment & dependencies

### Create and activate a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate      # deactivate with: deactivate
```

Keeps project dependencies isolated from your system Python — avoids version conflicts with other projects.

### Install dependencies

```bash
pip install -r requirements.txt        # runtime deps only (mirrors the Docker image)
pip install -r requirements-dev.txt     # runtime + pytest, ruff, pip-tools (for local dev)
```

`requirements-dev.txt` already includes `requirements.txt` via `-r requirements.in`, so one install gives you everything needed to develop, test, and lint.

### Add or update a dependency

```bash
# 1. Edit requirements.in (runtime) or requirements-dev.in (dev tooling)
# 2. Recompile the locked, hash-pinned files:
pip-compile --generate-hashes --strip-extras requirements.in
pip-compile --generate-hashes --strip-extras requirements-dev.in

# 3. Re-install to pick up the change
pip install -r requirements-dev.txt
```

Never hand-edit `requirements.txt` / `requirements-dev.txt` — they're generated. `pip-compile` resolves versions and pins hashes so installs are reproducible and tamper-evident (this is what `--require-hashes` in the Dockerfile enforces at build time).

---

## 2. Running the app

### Flask dev server (auto-reload, debug-friendly)

```bash
flask --app app/app.py run
flask --app app/app.py run --debug   # auto-reload on code changes + interactive debugger
```

Fastest inner loop for day-to-day development — no container rebuild needed.

### Gunicorn (matches production)

```bash
gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 app.app:app
```

This is exactly what the Dockerfile runs. Use it when you want to reproduce a production-like process model locally (e.g. debugging worker/thread behavior).

### Exercise the endpoints

```bash
curl localhost:5000/                 # or :8000 depending on how you started it
curl localhost:5000/health
curl -X POST localhost:5000/echo \
  -H 'Content-Type: application/json' \
  -d '{"hi":"there"}'
```

Quick manual smoke test without opening a browser.

---

## 3. Testing & linting

```bash
pytest                     # run the test suite
pytest -v                  # verbose, one line per test — useful when a test fails and you need to see which
pytest --cov=app           # test suite + coverage report

ruff check .                # lint for bugs/style issues
ruff check . --fix          # auto-fix what's safely fixable
ruff format .                # auto-format code
```

Run `pytest` and `ruff check .` before every push — this is exactly what CI runs, so catching failures locally saves a round trip through the pipeline.

---

## 4. Docker

### Build & run the app container

```bash
docker build -t flaskapp:dev .
docker run --name flaskapp -p 8000:8000 flaskapp:dev
docker run -d --name flaskapp -p 8000:8000 flaskapp:dev   # -d = detached, keeps your terminal free
```

Verifies the app works the same way it will in CI/production — the Dockerfile is the actual deployment artifact.

### Manage containers

```bash
docker ps                       # list running containers
docker logs -f flaskapp         # follow logs (Gunicorn access/error logs go to stdout)
docker exec -it flaskapp sh     # shell into the running container for debugging
docker stop flaskapp
docker rm flaskapp
```

`logs -f` is the fastest way to watch what the app is doing without instrumenting anything extra, since the Dockerfile routes Gunicorn's access/error logs to stdout.

### Clean up

```bash
docker image prune              # remove dangling (untagged) images
docker system prune             # remove all unused containers/images/networks — frees disk space
```

Multi-stage rebuilds during development leave behind dangling images; prune periodically so `docker build` output stays readable and disk doesn't fill up.

---

## 5. Platform stack (Gitea + registry + runner)

The self-hosted CI platform (Gitea, Gitea Actions runner, local Docker registry) lives in `platform/`, separate from the app itself.

### First-time setup

```bash
cp platform/.env.example platform/.env
# edit platform/.env: set GITEA_RUNNER_REGISTRATION_TOKEN once Gitea is up
# (Gitea -> Site Administration -> Actions -> Runners -> create registration token)
```

`platform/.env` is gitignored on purpose — it holds a registration token, so it must never be committed.

### Start / stop

```bash
docker compose --env-file platform/.env -f platform/compose.yaml up -d
docker compose --env-file platform/.env -f platform/compose.yaml down
```

Brings up Gitea (Git server + CI), the Actions runner, and the local image registry as one unit. `down` stops them without deleting data — it lives in named Docker volumes.

### Verify it's healthy

```bash
curl http://localhost:3000/api/healthz   # Gitea
curl http://localhost:5001/v2/           # Docker registry
```

Quick check that the platform came up correctly before you start pushing code and expecting CI to run.

### Reset platform data (destructive)

```bash
docker compose --env-file platform/.env -f platform/compose.yaml down -v
```

`-v` deletes the named volumes (`projecta-gitea-data`, `projecta-runner-data`, `projecta-registry-data`) — wipes Gitea's database, repos, and registry contents. Use only when you deliberately want a clean-slate platform (e.g. testing the "clean machine" setup path).

---

## 6. Git workflow

Trunk-based, short-lived branches off `main`, Conventional Commits, squash merge via PR. See [`docs/PROJECT-WORKFLOW.md`](PROJECT-WORKFLOW.md) for the full rationale.

```bash
git checkout main && git pull
git checkout -b feat/short-description        # branch naming: <type>/<kebab-description>

# ... make changes ...

git add <specific files>                       # avoid `git add -A` — review what you're staging
git commit -m "feat(app): add /metrics endpoint"
git rebase main                                 # keep branch current before opening a PR
git push -u origin feat/short-description
gh pr create --fill                             # open a PR instead of pushing straight to main
```

Branches older than ~2 days usually mean the change was too big — split it. Commit types: `feat`, `fix`, `docs`, `ci`, `build`, `refactor`, `test`, `chore`, `perf`. Squash-merge keeps `main`'s history one commit per story, which makes `git log` and reverts easy to reason about.

---

## Related docs

| Document | Contents |
|----------|----------|
| [`README.md`](../README.md) | Project overview, architecture, roadmap |
| [`docs/PROJECT-WORKFLOW.md`](PROJECT-WORKFLOW.md) | Branching, commits, PR, and board conventions in depth |
| [`docs/MANUAL-WALKTHROUGH.md`](MANUAL-WALKTHROUGH.md) | Original manual Docker build/run notes and the issue hit along the way |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | System architecture diagram |
| [`platform/platformREADME.md`](../platform/platformREADME.md) | Platform stack components and data persistence |
