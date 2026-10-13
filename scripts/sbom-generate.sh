#!/usr/bin/env bash
# Generate the CycloneDX SBOMs for one measured release, on the measurement VM.
#
# Runs ON the VM, piped over ssh from the laptop (docs/sbom/README.md,
# "Reproducing"):
#
#   git archive <tag> | ssh azureuser@<ip> 'rm -rf ~/sbom-src && mkdir ~/sbom-src && tar -x -C ~/sbom-src'
#   ssh azureuser@<ip> 'bash -s' -- <tag> < scripts/sbom-generate.sh
#   scp 'azureuser@<ip>:~/sbom-out/*' docs/sbom/
#
# Why on the VM and not on the laptop: the images to inventory are the ones the
# cluster actually runs, and they live in the VM's registry. Rebuilding them on
# the laptop would inventory a different artifact — an arm64 build of the same
# Dockerfile is not the amd64 image the measurement ran against.
#
# Why from a `git archive` and not a checkout: the filesystem SBOMs must
# describe exactly the tagged tree, with no working-tree edits and no .venv or
# node_modules that happen to exist locally.
set -euo pipefail

TAG="${1:?usage: sbom-generate.sh <short-sha>}"
# The same Trivy the CI pins, and pinned by digest here as well: the report
# states the digest, so the run has to use it.
TRIVY_IMAGE="aquasec/trivy:0.72.0@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f"
SRC="$HOME/sbom-src"
OUT="$HOME/sbom-out"

test -f "$SRC/requirements.txt" || {
  echo "no source tree at $SRC — unpack 'git archive $TAG' there first" >&2
  exit 1
}
rm -rf "$OUT"
mkdir -p "$OUT"

trivy() {
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$SRC":/work:ro -v "$OUT":/out -w /work \
    "$TRIVY_IMAGE" "$@"
}

log="$OUT/generation-$TAG.txt"
{
  echo "generated_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "tag: $TAG"
  echo "host: $(hostname)"
  echo "trivy_image: $TRIVY_IMAGE"
  echo "trivy_version: $(trivy --version | head -1)"
} > "$log"

# Filesystem: runtime dependencies (requirements.txt, frontend/package-lock.json).
trivy fs --format cyclonedx --skip-dirs .venv --skip-dirs .git \
  --output /out/projecta-repo-fs.cdx.json .

# Filesystem: development, CI and Ansible toolchain. Trivy's pip analyzer only
# matches the exact name requirements.txt, hence the patterns.
trivy fs --format cyclonedx --skip-dirs .venv --skip-dirs .git \
  --file-patterns 'pip:.*requirements-dev\.txt' \
  --file-patterns 'pip:.*requirements-(ansible|lint)\.txt' \
  --output /out/projecta-dev-toolchain.cdx.json .

# The two application images exactly as the cluster pulls them.
for app in flask frontend; do
  ref="localhost:5001/projecta-$app:$TAG"
  docker pull -q "$ref" >/dev/null
  echo "image projecta-$app: $(docker image inspect -f '{{index .RepoDigests 0}}' "$ref")" >> "$log"
  trivy image --format cyclonedx --output "/out/projecta-$app-$TAG.cdx.json" "$ref"
done

# The platform images the running containers were started from — not the tags
# in .env.example, which is what should run, rather than what does.
for c in projecta-gitea projecta-act-runner projecta-registry; do
  img=$(docker inspect -f '{{.Config.Image}}' "$c")
  out=$(echo "$img" | sed 's#.*/##; s#:#-#')
  echo "container $c: $img $(docker image inspect -f '{{index .RepoDigests 0}}' "$img")" >> "$log"
  trivy image --format cyclonedx --output "/out/platform-$out.cdx.json" "$img"
done

echo "done:"
ls -l "$OUT"
cat "$log"
