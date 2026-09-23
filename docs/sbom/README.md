# Software inventory / SBOM

Inventory of every software component ProjectA builds on, runs on, or is tested
with. **Third generation**, generated 2026-09-23 against commit `e4da1d9` — the
release the automated measurement series ran on and the one the cluster runs —
**on the measurement host** (`szakdoga2-vm`, amd64), from its own registry.

**Why a third generation.** Two reasons, and only the first was known before
the rescan. The 2026-09-22 base-image bump (last section) made the application
image SBOM describe an image that no longer exists. And the rescan showed that
the previous generation had described *arm64* builds made on the laptop, not
the amd64 images the cluster runs (finding 6).

**Valid for the current branch tip.** Verify with:

```bash
git diff --name-only e4da1d9..HEAD -- Dockerfile frontend/ requirements*.txt ansible/requirements* app/ .dockerignore
```

Empty output means no regeneration is needed. The guard is wider than the
previous one: it now covers the frontend and every requirement file, because
this generation inventories them.

The scope is **inventory and preparedness**, not a security audit. No
vulnerability data is included — `--format cyclonedx` disables the
vulnerability scanners by design.

## Scope note

| Asset | Present | Where |
|---|---|---|
| Dockerfile | yes, two | `Dockerfile`, `frontend/Dockerfile` |
| Compose file | yes, platform services | `platform/compose.yaml` |
| CI/CD pipeline | yes, **Gitea Actions** — not Jenkins | `.gitea/workflows/ci.yml` |
| Config management | yes, **Ansible** | `ansible/` |
| Kubernetes manifests | yes, **Helm chart** | `chart/` |
| Jenkinsfile | no | — |

The Kubernetes row changed since the previous generation: the chart was added
with the move to k3s (ADR-0009).

## Tool

| | |
|---|---|
| Tool | Trivy |
| Version | 0.72.0 |
| Image digest | `sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f` |
| SBOM format | CycloneDX 1.7 (JSON) |
| Output location | `docs/sbom/` |
| Run record | `generation-e4da1d9.txt` — time, host, Trivy, and the digest of every scanned image |

## How it was generated

One script, run on the measurement VM over ssh, from the laptop's repository
root:

```bash
IP=$(terraform -chdir=terraform output -raw public_ip)
git archive e4da1d9 | ssh azureuser@$IP 'rm -rf ~/sbom-src && mkdir ~/sbom-src && tar -x -C ~/sbom-src'
ssh azureuser@$IP 'bash -s' -- e4da1d9 < scripts/sbom-generate.sh
scp "azureuser@$IP:~/sbom-out/*" docs/sbom/
python3 scripts/sbom-inventory-xlsx.py e4da1d9
```

The script (`scripts/sbom-generate.sh`) carries the reasoning in its comments.
In short: the filesystem scans run on a `git archive` of the tag, so no local
edit, `.venv` or `node_modules` leaks in; the image scans pull the two
application images from the VM's registry, so the SBOM describes the artifact
the cluster runs; the platform scans use the image each *running* container
was started from, not the tag in `.env.example`. The `--file-patterns` flags of
the toolchain scan are unchanged (finding 5).

## Generated files

| File | Subject | Components |
|---|---|---|
| `projecta-repo-fs.cdx.json` | `requirements.txt` + `frontend/package-lock.json` | 18 |
| `projecta-dev-toolchain.cdx.json` | dev, CI, Ansible and lint requirement files | 107 (73 unique) |
| `projecta-flask-e4da1d9.cdx.json` | backend image (Debian 13.7) | 102 (1 OS + 87 deb + 14 pypi) |
| `projecta-frontend-e4da1d9.cdx.json` | frontend image (Alpine 3.21.3) — **new** | 69 (1 OS + 68 apk) |
| `platform-gitea-1.27.0.cdx.json` | Gitea server image (Alpine 3.24.1) | 340 |
| `platform-act_runner-0.2.12.cdx.json` | Actions runner image (Alpine 3.22.0) | 116 |
| `platform-registry-2.cdx.json` | Docker registry image (Alpine 3.18.12) | 19 |

Total: **771 components** across seven SBOMs (previous generation: 621 across
six). The spreadsheet view, `ProjectA-software-inventory-2026-09-23.xlsx`, is
generated from these files by `scripts/sbom-inventory-xlsx.py`; if the two ever
disagree, the JSONs win. `projecta-flask-a6a4d33.cdx.json` and the 2026-08-03
spreadsheet are retired; git history keeps them.

## What changed since the previous generation

Compared on (ecosystem, name, version). Nothing was removed anywhere.

| SBOM | Changed | Added | Why |
|---|---:|---:|---|
| backend image | 26 | 4 | Debian 13.6 → 13.7 (the base-image bump: `util-linux` family, `openssl`, `libc6`, `perl-base`, `gzip`, `libsqlite3-0`, `libpcre2-8-0`, `tzdata`, …) and the runtime dependencies added since: `psycopg`, `psycopg-binary`, `prometheus_client`, `typing_extensions` |
| repo filesystem | 0 | 8 | the same four Python packages, and the frontend's lockfile with its three production npm packages (`react`, `react-dom`, `scheduler`) |
| dev toolchain | 0 | 43 unique | the lint and Ansible requirement files grew with the pipeline (ansible-lint's dependency tree: `ansible-compat`, `black`, `yamllint`, `ruamel-yaml`, `jsonschema`, …) and the new runtime packages |
| three platform images | 0 | 0 | same versions — but a different architecture (finding 6) |
| frontend image | — | 69 | first inventory |

The 26 backend changes include the 43 CI findings of 2026-09-22 seen from the
other side: every package family named there (`util-linux`, `perl-base`, `libpcre2`,
`libsqlite3`, `openssl`, `gzip`) are the ones that moved.

## Components not covered by any SBOM

CycloneDX captures package ecosystems. It does not capture pipeline tooling,
base-image pins or Galaxy collections, so those are listed here by hand.

| Component | Version | Source file | Pinning |
|---|---|---|---|
| Python (runtime + CI) | 3.12 | `Dockerfile`, `.gitea/workflows/ci.yml` | minor version |
| Backend base image `python:3.12-slim` | digest `sha256:2f17fc04…06a9` | `Dockerfile` | **digest** |
| Debian (in backend base image) | 13.7 | derived | inherited from digest |
| Frontend build image `node:22-alpine` | 22-alpine | `frontend/Dockerfile` | tag |
| Frontend runtime image `nginxinc/nginx-unprivileged` | 1.27-alpine (Alpine 3.21.3) | `frontend/Dockerfile` | tag |
| Gitea | 1.27.0 | `platform/.env.example` | exact tag |
| Gitea act_runner | 0.2.12 | `platform/.env.example` | exact tag |
| Docker Registry | 2 (running: `sha256:a3d8aaa6…5373`) | `platform/.env.example` | **floating major tag** |
| Helm (deploy job) | 3.22.0 (`alpine/helm`) | `.gitea/workflows/ci.yml` | exact tag |
| ansible-core | 2.21.2 | `ansible/requirements-ansible.txt` | exact + hash |
| requests (Ansible control node) | 2.33.0 | `ansible/requirements-ansible.txt` | exact + hash |
| ansible-lint | 26.6.0 | `ansible/requirements-lint.txt` | exact + hash |
| community.docker collection | 4.8.7 | `ansible/requirements.yml` | exact |
| hadolint | v2.14.0 | `.gitea/workflows/ci.yml` | exact tag |
| Trivy (in CI) | 0.72.0 | `.gitea/workflows/ci.yml` | exact tag |
| Trivy (this report) | 0.72.0 | `scripts/sbom-generate.sh` | exact + digest |
| `actions/checkout` | v4 | `.gitea/workflows/ci.yml` | major tag |
| `actions/setup-python` | v5 | `.gitea/workflows/ci.yml` | major tag |
| Coverage gate | 80% minimum | `.gitea/workflows/ci.yml` | — |

## Findings

Findings 1 and 2 were raised by the 2026-07-31 generation and closed by the
2026-08-03 one; 6 was raised and closed by this (2026-09-23) generation. They
are kept rather than deleted: an inventory whose findings vanish once fixed
cannot show that it was ever worth running.

1. ~~**gunicorn version drift between production and CI.**~~ **Closed** in
   `c6ddbf9` (#28). `requirements.txt` pinned `gunicorn==23.0.0` while
   `requirements-dev.txt` pinned `gunicorn==26.0.0`; both compiled from a
   `requirements.in` that left gunicorn unpinned, so the two lockfiles were
   compiled at different times and diverged. Every other shared package matched
   exactly, which is what made it easy to miss — and what made an SBOM the tool
   that caught it. Fixed by pinning the runtime dependencies in
   `requirements.in` and recompiling both lockfiles in one commit.

   A second cause was found while fixing it: `docs/DEVELOPMENT.md` documented a
   `pip-compile` invocation missing `--allow-unsafe`, so anyone following the
   documentation would have regenerated the dev lock without its `pip`,
   `setuptools` and `wheel` pins. Corrected in the same commit. The drift had
   two sources, and pinning alone would have left one of them live.

2. ~~**Trivy is the one unpinned tool in the pipeline.**~~ **Closed.**
   `.gitea/workflows/ci.yml` ran `aquasec/trivy:latest` while hadolint,
   ansible-core, ansible-lint, community.docker and the base image were all
   pinned exactly. Now pinned to `0.72.0` — the same version that produces this
   report, so the scanner that gates the build is the scanner that inventories
   it.

3. **`registry:2` is a floating major tag**, so the registry can change
   underneath the platform between `docker compose pull` runs. **Open.**

   Mitigated in this generation: `scripts/sbom-generate.sh` records the
   digest the running registry container was started from
   (`generation-e4da1d9.txt`), so the report at least says which image it
   inventoried.

4. **License data is absent from the filesystem SBOMs.** Trivy's pip analyzer
   needs an installed `site-packages` tree to read license metadata, and none
   exists inside the scanner container. The image SBOM does carry licenses,
   because the packages are installed there. If license inventory is needed
   from the filesystem scan, it has to run outside the container against the
   active virtualenv. **Open.**

5. **Trivy's pip analyzer only matches the exact filename `requirements.txt`.**
   Without the `--file-patterns` flags the dev, Ansible and lint requirement
   files are silently left out. Kept in `scripts/sbom-generate.sh`. **Open
   (mitigated).**

6. ~~**The previous generation described arm64 artifacts, not the measured
   ones.**~~ **Closed** by this generation. Every architecture-specific purl in
   the 2026-08-03 image SBOMs carried `arm64`/`aarch64`; every one in this
   generation carries `amd64`/`x86_64`. The earlier image SBOM inventoried a
   laptop build of the Dockerfile, and the platform SBOMs the laptop's platform
   — before the platform moved to Azure (naplo 2.4). For the three platform
   images the package names and versions are identical across the two
   architectures, which is exactly why nothing in the component lists gave it
   away: the difference is only in the purl qualifier. This generation runs on
   the measurement host against its registry, by construction.

7. **The frontend image SBOM cannot see the frontend's JavaScript
   dependencies.** The `projecta-frontend` image SBOM lists 68 Alpine packages
   and the OS, and no npm component: the runtime stage is nginx serving static
   files, and React is bundled into them. An image-only inventory would conclude
   that the frontend carries no third-party code. The npm dependencies are in
   `projecta-repo-fs.cdx.json`, read from `frontend/package-lock.json`. **Open,
   by design** — it is a property of the artifact, not of the scan.

8. **The frontend base images are tag-pinned and not scanned in CI.**
   `node:22-alpine` and `nginxinc/nginx-unprivileged:1.27-alpine` in
   `frontend/Dockerfile`; the scanned runtime layer is Alpine 3.21.3. Recorded
   with the frontend build step in `ci.yml` and deliberately not closed before
   the measurement series (see the base-image bump section below). **Open.**

## Guard history

The 2026-07-31 generation shipped with a staleness check: a `git diff` over
`Dockerfile`, `requirements.txt`, `app/` and `.dockerignore`, with the rule that
any output means rebuild and rescan.

It fired on 2026-08-03, three days later, against the commit that fixed finding
1 — the report's own finding invalidated the report. That is the guard working,
and it is the reason this file is a second generation rather than a stale first
one.

Worth stating plainly, because someone will ask: the guard is **path-based, not
content-based**, and this time it was conservative. The only change to
`requirements.txt` was its pip-compile header comment; the package set was
identical and the image SBOM came back unchanged component-for-component. The
guard demanded a rescan that, strictly, changed nothing about the image.

That is the correct trade. A guard that decides which diffs "count" is a guard
that will eventually decide wrongly, and it will do so silently. A guard that
occasionally costs a rescan you did not need fails in the direction you can
afford.

**The third generation adds a second lesson.** The guard is about *content*:
it fires when the inputs change. It cannot notice that the artifact scanned was
never the artifact deployed — the arm64 build passed every path check, because
the paths were right and the machine was wrong. That failure mode is closed by
*where* the scan runs, not by what it checks, which is why the generation now
happens on the measurement host by script.

## Reproducing

Everything above is reproducible with the commands in "How it was generated".
Nothing was collected by hand except the table of components not covered by any
SBOM, which is read directly from the source files cited in it.

## Possible follow-up

Adding an SBOM step to `.gitea/workflows/ci.yml` on a `schedule:` trigger would
keep this inventory current without anyone remembering to run it. Deliberately
out of scope for this task, which is a point-in-time inventory.

## Base-image bump — 2026-09-22

The digest above was `sha256:57cd7c3a…710de` (Debian 13.6) until this date. It
was not changed for a new feature; it was changed because the image scan in
`ci.yml` failed on a commit that touched neither the Dockerfile nor any
dependency.

**What happened.** Trivy 0.72.0 refreshed its vulnerability database and
reported 43 findings against the pinned base image — 40 HIGH, 3 CRITICAL, all
of them Debian packages (`util-linux`, `perl-base`, `libpcre2`, `libsqlite3`,
`openssl`, `gzip`) and all with a fixed version available, which is why
`--ignore-unfixed` did not filter them. Nothing in the application's own
dependency set was implicated: every `python-pkg` target came back clean.

`python:3.12-slim` had meanwhile been rebuilt on Debian 13.7, and a scan of
that image returns zero findings, so the fix is the digest bump and nothing
else.

**Why it is worth writing down.** The pipeline pins the scanner precisely so a
build cannot fail for a reason unrelated to its own change — that argument is
in `.gitea/workflows/ci.yml` on both Trivy steps and in ADR-0005. Pinning the
scanner does not pin its database, and it cannot: a vulnerability database that
does not change is a vulnerability database that is wrong. So a green image
scan is not a property of the artifact alone. It is a statement about the
artifact *and the day it was scanned*, and its shelf life is however long it
takes for the next advisory to land against the base image.

The practical consequence for this project is that a reproducible build and a
clean scan are different guarantees. The digest pin delivers the first
unconditionally; the second has to be re-earned, and the only mechanism that
re-earns it is a pipeline that runs the scan on every commit. A deployment
route without that gate does not fail — it simply never asks the question.

**Not covered by this bump:** the frontend image (`node:22-alpine`,
`nginxinc/nginx-unprivileged:1.27-alpine`) is pinned by tag rather than by
digest and is not scanned in CI. That is a known gap, recorded with the
frontend build step in `ci.yml`, and it is not closed here: introducing a new
gate immediately before a measurement series is how a series gets burned by a
failure that has nothing to do with what is being measured.
