#!/usr/bin/env python3
"""Build the spreadsheet view of docs/sbom/ from the CycloneDX files.

    python3 scripts/sbom-inventory-xlsx.py e4da1d9

The workbook is a derived view. Every per-SBOM sheet and every component
count is read from the JSONs, so the two cannot disagree; the only
hand-maintained content is KEY_VERSIONS and FINDINGS below, which cover what
CycloneDX does not (pins, base-image digests, CI tooling) and what the
inventory concluded. Those two tables are read from the source files named in
their own "Source file" column — change the file, then change the row.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

TAG = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: sbom-inventory-xlsx.py <short-sha>")
ROOT = Path(__file__).resolve().parent.parent
SBOM = ROOT / "docs" / "sbom"
GEN = dict(
    line.split(": ", 1)
    for line in (SBOM / f"generation-{TAG}.txt").read_text().splitlines()
    if ": " in line
)
DATE = GEN["generated_utc"][:10]
FULL_SHA = subprocess.run(
    ["git", "rev-parse", TAG], cwd=ROOT, capture_output=True, text=True, check=True
).stdout.strip()

HEAD_FILL = PatternFill("solid", fgColor="1F3864")
HEAD_FONT = Font(bold=True, color="FFFFFF")
WRAP = Alignment(wrap_text=True, vertical="top")

# (file stem, sheet name, subject)
SBOMS = [
    ("projecta-repo-fs", "Runtime deps", "repository tree: requirements.txt, frontend/package-lock.json"),
    ("projecta-dev-toolchain", "Dev+CI deps", "repository tree: dev, CI, Ansible and lint requirement files"),
    (f"projecta-flask-{TAG}", "Flask image", f"localhost:5001/projecta-flask:{TAG}"),
    (f"projecta-frontend-{TAG}", "Frontend image", f"localhost:5001/projecta-frontend:{TAG}"),
    ("platform-gitea-1.27.0", "Platform gitea", "docker.gitea.com/gitea:1.27.0"),
    ("platform-act_runner-0.2.12", "Platform act_runner", "docker.io/gitea/act_runner:0.2.12"),
    ("platform-registry-2", "Platform registry", "registry:2"),
]

KEY_VERSIONS = [
    ("Python (runtime + CI)", "3.12", "Language", "Dockerfile / .gitea/workflows/ci.yml", "Minor version", None),
    ("python:3.12-slim (backend base image)", "sha256:2f17fc04…06a9", "Container", "Dockerfile", "Digest",
     "Bumped 2026-09-22 from sha256:57cd7c3a…710de (Debian 13.6) after the CI image scan failed on 43 base-image findings"),
    ("Debian (in backend base image)", "13.7", "OS", "derived from base image", "Inherited", "Was 13.6"),
    ("node:22-alpine (frontend build stage)", "22-alpine", "Container", "frontend/Dockerfile", "Tag", "Not in the shipped image"),
    ("nginxinc/nginx-unprivileged (frontend runtime)", "1.27-alpine", "Container", "frontend/Dockerfile", "Tag",
     "Alpine 3.21.3 in the scanned image; not digest-pinned, not scanned in CI — see Findings"),
    ("Flask", "3.1.3", "Runtime dep", "requirements.txt", "Exact + hash", None),
    ("gunicorn", "23.0.0", "Runtime dep", "requirements.txt / requirements-dev.txt", "Exact + hash", "Same in production and CI"),
    ("psycopg (+ binary)", "3.3.5", "Runtime dep", "requirements.txt", "Exact + hash", "Added after the 2026-08-03 generation"),
    ("prometheus-client", "0.26.0", "Runtime dep", "requirements.txt", "Exact + hash", "Added after the 2026-08-03 generation"),
    ("React / react-dom", "19.3.0", "Frontend dep", "frontend/package-lock.json", "Lockfile", "Bundled into static JS; invisible to the image SBOM"),
    ("Gitea", "1.27.0", "Platform", "platform/.env.example", "Exact tag", None),
    ("Gitea act_runner", "0.2.12", "Platform", "platform/.env.example", "Exact tag", None),
    ("Docker Registry", "2", "Platform", "platform/.env.example", "Floating major tag",
     "Running digest recorded in generation-" + TAG + ".txt"),
    ("Helm (deploy job)", "3.22.0", "CD tooling", ".gitea/workflows/ci.yml", "Exact tag", "alpine/helm image"),
    ("ansible-core", "2.21.2", "Config mgmt", "ansible/requirements-ansible.txt", "Exact + hash", None),
    ("requests (control node)", "2.33.0", "Config mgmt", "ansible/requirements-ansible.txt", "Exact + hash", None),
    ("ansible-lint", "26.6.0", "CI tooling", "ansible/requirements-lint.txt", "Exact + hash", None),
    ("community.docker collection", "4.8.7", "Config mgmt", "ansible/requirements.yml", "Exact", "Not covered by CycloneDX"),
    ("hadolint", "v2.14.0", "CI tooling", ".gitea/workflows/ci.yml", "Exact tag", None),
    ("Trivy (CI and this report)", "0.72.0", "CI tooling", ".gitea/workflows/ci.yml / scripts/sbom-generate.sh",
     "Exact tag (CI), exact + digest (report)", None),
    ("ruff", "0.15.22", "CI tooling", "requirements-dev.txt", "Exact + hash", None),
    ("pytest / pytest-cov", "9.1.1 / 7.1.0", "CI tooling", "requirements-dev.txt", "Exact + hash", None),
    ("pip-tools", "7.6.0", "CI tooling", "requirements-dev.txt", "Exact + hash", None),
    ("actions/checkout", "v4", "CI tooling", ".gitea/workflows/ci.yml", "Major tag", None),
    ("actions/setup-python", "v5", "CI tooling", ".gitea/workflows/ci.yml", "Major tag", None),
    ("Coverage gate", "80% minimum", "CI policy", ".gitea/workflows/ci.yml", "—", None),
]

FINDINGS = [
    (1, "gunicorn version drift between production and CI",
     "requirements.txt pinned 23.0.0, requirements-dev.txt pinned 26.0.0.",
     "CI tested against a different gunicorn than the image shipped.",
     "Pinned in requirements.in, both lockfiles recompiled in one commit.", "RESOLVED — c6ddbf9 (#28)"),
    (2, "Trivy was the only unpinned tool in the pipeline", "ci.yml used aquasec/trivy:latest.",
     "A scanner that gains a rule overnight fails a build nobody touched.",
     "Pinned to 0.72.0 — the same version that generates this report.", "RESOLVED"),
    (3, "registry:2 is a floating major tag", "REGISTRY_VERSION=2 in platform/.env.example.",
     "The registry image can change underneath the platform between pulls.",
     "Pin to an exact version. Until then, the running digest is recorded per generation.", "OPEN"),
    (4, "License data absent from filesystem SBOMs",
     "Trivy: 'Unable to find python site-packages directory. License detection is skipped.'",
     "The pip analyzer needs an installed site-packages tree. The image SBOMs do carry licenses.",
     "Run outside the container against a virtualenv if filesystem license data is needed.", "OPEN"),
    (5, "Trivy's pip analyzer only matches the exact filename requirements.txt",
     "Without --file-patterns the dev, Ansible and lint requirement files are silently omitted.",
     "An SBOM step without the patterns would under-report the toolchain.",
     "Kept in scripts/sbom-generate.sh.", "OPEN (mitigated)"),
    (6, "The previous generation described arm64 artifacts, not the measured ones",
     "Every architecture-specific purl in the 2026-08-03 image SBOMs carried arm64/aarch64 (arch=all aside); this "
     "generation's carry amd64/x86_64. Package names and versions of the three platform images are identical.",
     "The earlier image SBOM inventoried a laptop build of the Dockerfile, not the image the cluster runs.",
     "Generate on the measurement host from the registry (scripts/sbom-generate.sh).", "RESOLVED — this generation"),
    (7, "The frontend image SBOM cannot see the frontend's JavaScript dependencies",
     "projecta-frontend image: 68 apk packages + OS, no npm component. React is bundled into static files.",
     "An image-only inventory would conclude the frontend has no third-party code.",
     "Read the npm dependencies from the filesystem SBOM (frontend/package-lock.json).", "OPEN (by design)"),
    (8, "Frontend base images are tag-pinned and not scanned in CI",
     "frontend/Dockerfile: node:22-alpine, nginxinc/nginx-unprivileged:1.27-alpine.",
     "The shipped nginx layer can change between builds without a gate noticing.",
     "Digest-pin and add the image scan — deferred until after the measurement series (ci.yml comment).", "OPEN"),
]


def style_header(ws, row=1):
    for cell in ws[row]:
        if cell.value is not None:
            cell.fill, cell.font = HEAD_FILL, HEAD_FONT


def table(ws, header, rows, widths):
    ws.append(header)
    for r in rows:
        ws.append(list(r))
    style_header(ws)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{chr(64 + len(header))}{ws.max_row}"
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = WRAP


def components(stem):
    doc = json.loads((SBOM / f"{stem}.cdx.json").read_text())
    raw = doc.get("components", [])
    seen, rows = set(), []
    for c in raw:
        purl = c.get("purl")
        key = (c.get("name"), c.get("version"), purl)
        if key in seen:
            continue
        seen.add(key)
        eco = re.match(r"pkg:([^/]+)/", purl).group(1) if purl else None
        lic = ", ".join(
            l.get("license", {}).get("id") or l.get("license", {}).get("name") or l.get("expression", "")
            for l in c.get("licenses", [])
        ) or None
        rows.append((c.get("name"), c.get("version"), c.get("type"), eco, lic, purl))
    order = {"operating-system": 0, "application": 1}
    rows.sort(key=lambda r: (order.get(r[2], 2), r[3] or "", r[0] or ""))
    return len(raw), rows


wb = Workbook()
ws = wb.active
ws.title = "Summary"
ws.append(["ProjectA — Software Inventory"])
ws["A1"].font = Font(bold=True, size=14, color="1F3864")
ws.append(["Point-in-time inventory of the software the measured release builds on, runs on, and is tested with."])
ws.append([])
ws.append(["Field", "Value"])
style_header(ws, 4)
for k, v in [
    ("Report date", DATE),
    ("Repository", "MilanProjA-Szakdoga"),
    ("Commit", f"{FULL_SHA} ({TAG})"),
    ("Generated on", f"{GEN['host']} (amd64) — the measurement host, from its registry"),
    ("Tool", GEN["trivy_version"].replace("Version: ", "Trivy ")),
    ("Tool image", GEN["trivy_image"]),
    ("SBOM format", "CycloneDX 1.7 (JSON)"),
    ("Output location", "docs/sbom/"),
    ("Scope", "Inventory and preparedness — not a security audit. No vulnerability data included."),
]:
    ws.append([k, v])
ws.append([])
ws.append(["Deployment assets reviewed"])
ws.append(["Asset", "Status", "Path"])
style_header(ws, ws.max_row)
for r in [
    ("Dockerfile (backend, frontend)", "Yes", "Dockerfile, frontend/Dockerfile"),
    ("Compose file", "Yes — platform services", "platform/compose.yaml"),
    ("CI/CD pipeline", "Yes — Gitea Actions, not Jenkins", ".gitea/workflows/ci.yml"),
    ("Config management", "Yes — Ansible", "ansible/"),
    ("Kubernetes manifests", "Yes — Helm chart", "chart/"),
    ("Jenkinsfile", "Not present in this project", "—"),
]:
    ws.append(list(r))
ws.append([])
ws.append([f"Validity: generated against {TAG}, the release the measurement series ran on. Re-verify with: "
           f"git diff --name-only {TAG}..HEAD -- Dockerfile frontend/ requirements*.txt ansible/requirements* app/ .dockerignore"])
ws.column_dimensions["A"].width = 32
ws.column_dimensions["B"].width = 70
ws.column_dimensions["C"].width = 34
for row in ws.iter_rows(min_row=5):
    for c in row:
        c.alignment = WRAP

table(wb.create_sheet("Key versions"),
      ["Component", "Version", "Category", "Source file", "Pinning method", "Note"],
      KEY_VERSIONS, [40, 22, 14, 42, 24, 60])
table(wb.create_sheet("Findings"),
      ["#", "Finding", "Evidence", "Impact", "Action", "Status"],
      FINDINGS, [5, 42, 55, 50, 45, 26])

counts, listings = [], {}
for stem, sheet, subject in SBOMS:
    n, rows = components(stem)
    counts.append((f"{stem}.cdx.json", subject, n, len(rows), "CycloneDX 1.7", "trivy 0.72.0"))
    listings[sheet] = rows
sf = wb.create_sheet("SBOM files")
table(sf, ["File", "Subject", "Components (raw)", "Unique (name, version, purl)", "Spec", "Generated by"],
      counts, [40, 52, 16, 16, 15, 14])
sf.append([])
sf.append([f"Total: {sum(c[2] for c in counts)} raw components across {len(counts)} SBOMs. "
           "'Raw' is the count in the CycloneDX file; the listing sheets de-duplicate, because the "
           "filesystem scans parse requirements.txt both on its own and as an include of the dev lockfile."])
for sheet, rows in listings.items():
    table(wb.create_sheet(sheet), ["Name", "Version", "Type", "Ecosystem", "Licenses", "PURL"],
          rows, [42, 30, 18, 12, 40, 70])

out = SBOM / f"ProjectA-software-inventory-{DATE}.xlsx"
wb.save(out)
print(out.relative_to(ROOT))
for c in counts:
    print(f"  {c[0]}: {c[2]} raw, {c[3]} unique")
print(f"  total raw: {sum(c[2] for c in counts)}")
