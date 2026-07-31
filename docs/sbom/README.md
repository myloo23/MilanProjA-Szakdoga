# Software inventory / SBOM

Ad-hoc inventory of every software component ProjectA builds on, runs on, or is
tested with. Generated 2026-07-31 against commit `2a2c371`.

**Still valid for the current branch tip.** Commits made after `2a2c371` add
`docs/sbom/` and nothing else — `Dockerfile`, `requirements.txt`, `app/` and
`.dockerignore` are byte-identical, so the image these SBOMs describe is the
image this branch still builds. Verify with:

```bash
git diff --name-only 2a2c371..HEAD -- Dockerfile requirements.txt app/ .dockerignore
```

Empty output means no regeneration is needed. If that command ever prints a
path, rebuild and rescan before reusing this report.

The scope is **inventory and preparedness**, not a security audit. No
vulnerability data is included — `--format cyclonedx` disables the vulnerability
scanners by design, and adding them would answer a different question than the
one asked.

## Scope note

The generic deployment-asset checklist asks for Dockerfiles, docker-compose
files, Kubernetes manifests and Jenkins pipelines. Two of those do not exist
here, and their absence is a fact about the project rather than a gap in this
report:

| Asset | Present | Where |
|---|---|---|
| Dockerfile | yes | `Dockerfile` |
| Compose file | yes | `platform/compose.yaml` |
| CI pipeline | yes, **Gitea Actions** — not Jenkins | `.gitea/workflows/ci.yml` |
| Config management | yes, **Ansible** | `ansible/` |
| Kubernetes manifests | no | — |
| Jenkinsfile | no | — |

## Tool

| | |
|---|---|
| Tool | Trivy |
| Version | 0.72.0 |
| Image digest | `sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f` |
| SBOM format | CycloneDX 1.7 (JSON) |
| Output location | `docs/sbom/` |

## Commands executed

Runtime dependencies (what ships):

```bash
docker run --rm -v "$PWD":/work -w /work \
  aquasec/trivy:0.72.0 \
  fs --format cyclonedx --skip-dirs .venv --skip-dirs .git \
  --output docs/sbom/projecta-repo-fs.cdx.json .
```

Development and CI toolchain. The `--file-patterns` flags are required: Trivy's
pip analyzer matches the exact filename `requirements.txt`, so the dev, Ansible
and lint requirement files are invisible to it by default.

```bash
docker run --rm -v "$PWD":/work -w /work \
  aquasec/trivy:0.72.0 \
  fs --format cyclonedx --skip-dirs .venv --skip-dirs .git \
  --file-patterns 'pip:.*requirements-dev\.txt' \
  --file-patterns 'pip:.*requirements-(ansible|lint)\.txt' \
  --output docs/sbom/projecta-dev-toolchain.cdx.json .
```

Application image, including the Debian base layer:

```bash
SHA=$(git rev-parse --short HEAD)
docker build -t localhost:5001/projecta-flask:$SHA .
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$PWD":/work -w /work \
  aquasec/trivy:0.72.0 \
  image --format cyclonedx \
  --output docs/sbom/projecta-flask-$SHA.cdx.json \
  localhost:5001/projecta-flask:$SHA
```

Platform images:

```bash
for img in docker.gitea.com/gitea:1.27.0 docker.io/gitea/act_runner:0.2.12 registry:2; do
  out=$(echo "$img" | sed 's#.*/##; s#:#-#')
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD":/work -w /work \
    aquasec/trivy:0.72.0 \
    image --format cyclonedx --output "docs/sbom/platform-$out.cdx.json" "$img"
done
```

## Generated files

| File | Subject | Components |
|---|---|---|
| `projecta-repo-fs.cdx.json` | `requirements.txt` — runtime deps | 10 |
| `projecta-dev-toolchain.cdx.json` | dev, CI and Ansible deps | 38 |
| `projecta-flask-2a2c371.cdx.json` | application image | 98 (1 OS + 87 deb + 10 pypi) |
| `platform-gitea-1.27.0.cdx.json` | Gitea server image (Alpine 3.24.1) | 340 |
| `platform-act_runner-0.2.12.cdx.json` | Actions runner image (Alpine 3.22.0) | 116 |
| `platform-registry-2.cdx.json` | Docker registry image (Alpine 3.18.12) | 19 |

Total: **621 components** across six SBOMs. A consolidated spreadsheet view is
in `ProjectA-software-inventory-2026-07-31.xlsx` alongside this file.

The three platform images run three different Alpine releases — 3.24.1, 3.22.0
and 3.18.12 — because each upstream pins its own base. The registry's 3.18.12
is the oldest by a wide margin, which follows from `registry:2` being a
floating major tag that upstream has effectively stopped moving.

## Components not covered by any SBOM

CycloneDX captures package ecosystems. It does not capture pipeline tooling,
base-image pins or Galaxy collections, so those are listed here by hand. This
table is the actual answer to "what software versions is the project using".

| Component | Version | Source file | Pinning |
|---|---|---|---|
| Python (runtime + CI) | 3.12 | `Dockerfile`, `.gitea/workflows/ci.yml` | minor version |
| Base image `python:3.12-slim` | digest `sha256:57cd7c3a…710de` | `Dockerfile` | **digest** |
| Debian (in base image) | 13.6 | derived | inherited from digest |
| Gitea | 1.27.0 | `platform/.env.example` | exact tag |
| Gitea act_runner | 0.2.12 | `platform/.env.example` | exact tag |
| Docker Registry | 2 | `platform/.env.example` | **floating major tag** |
| ansible-core | 2.21.2 | `ansible/requirements-ansible.txt` | exact |
| requests (Ansible control node) | 2.32.3 | `ansible/requirements-ansible.txt` | exact |
| ansible-lint | 26.6.0 | `ansible/requirements-lint.txt` | exact |
| community.docker collection | 4.8.7 | `ansible/requirements.yml` | exact |
| hadolint | v2.14.0 | `.gitea/workflows/ci.yml` | exact tag |
| Trivy (in CI) | `latest` | `.gitea/workflows/ci.yml` | **unpinned** |
| Trivy (this report) | 0.72.0 | this document | exact + digest |
| `actions/checkout` | v4 | `.gitea/workflows/ci.yml` | major tag |
| `actions/setup-python` | v5 | `.gitea/workflows/ci.yml` | major tag |
| Coverage gate | 80% minimum | `.gitea/workflows/ci.yml` | — |

## Findings

1. **gunicorn version drift between production and CI.** `requirements.txt`
   pins `gunicorn==23.0.0`; `requirements-dev.txt` pins `gunicorn==26.0.0`.
   Both compile from `requirements.in`, which leaves gunicorn unpinned, so the
   two lockfiles were compiled at different times and diverged. CI runs the
   test suite against gunicorn 26 while the image ships gunicorn 23. Every
   other shared package matches exactly, which is what makes this easy to miss.
   Recompiling both lockfiles from the same `requirements.in` in one commit
   resolves it.

2. **Trivy is the one unpinned tool in the pipeline.** `.gitea/workflows/ci.yml`
   uses `aquasec/trivy:latest` while hadolint, ansible-core, ansible-lint,
   community.docker and the base image are all pinned exactly. A scanner that
   gains a rule overnight fails a build nobody touched — the same argument the
   repo already makes for hadolint.

3. **`registry:2` is a floating major tag**, so the registry can change
   underneath the platform between `docker compose pull` runs.

4. **License data is absent from the filesystem SBOMs.** Trivy's pip analyzer
   needs an installed `site-packages` tree to read license metadata, and none
   exists inside the scanner container. The image SBOM does carry licenses,
   because the packages are installed there. If license inventory is needed
   from the filesystem scan, it has to run outside the container against the
   active virtualenv.

## Reproducing

Everything above is reproducible from a clean checkout with the commands in
this file. Nothing was collected by hand except the table of components not
covered by any SBOM, which is read directly from the source files cited in its
last-but-one column.

## Possible follow-up

Adding an SBOM step to `.gitea/workflows/ci.yml` on a `schedule:` trigger would
keep this inventory current without anyone remembering to run it. Deliberately
out of scope for this task, which is a point-in-time inventory.
