#!/usr/bin/env bash
#
# deploy.sh — build the kidspoints image and push it to a container
# registry. Tags the build with the short git SHA and also moves :latest.
#
# Run from the repo root (or anywhere — we cd to the repo root ourselves).
# Re-run any time you want to ship a new build; it's idempotent.
#
# Required:
#   REGISTRY     e.g. ghcr.io/youruser, docker.io/youruser, 192.168.1.10:5000
# Optional:
#   IMAGE_NAME   default: kidspoints
#   ALLOW_DIRTY  set to 1 to skip the clean-tree check (NOT recommended)
#
# Values can be exported in the shell or placed in a .env at the repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

: "${REGISTRY:?REGISTRY is required (e.g. ghcr.io/youruser). See .env.example.}"
IMAGE_NAME="${IMAGE_NAME:-kidspoints}"
IMAGE_REF="${REGISTRY}/${IMAGE_NAME}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "deploy.sh: must run inside a git repository" >&2
    exit 1
fi

if [ "${ALLOW_DIRTY:-0}" != "1" ]; then
    if [ -n "$(git status --porcelain)" ]; then
        echo "deploy.sh: working tree is dirty — commit or stash first." >&2
        echo "           (set ALLOW_DIRTY=1 to override, but :latest will" >&2
        echo "            then point at an unreproducible build.)" >&2
        git status --short >&2
        exit 1
    fi
fi

SHA="$(git rev-parse --short HEAD)"
SHA_TAG="${IMAGE_REF}:${SHA}"
LATEST_TAG="${IMAGE_REF}:latest"

echo "==> Building ${SHA_TAG}"
DOCKER_BUILDKIT=1 docker build \
    --tag "${SHA_TAG}" \
    --tag "${LATEST_TAG}" \
    .

echo "==> Pushing ${SHA_TAG}"
docker push "${SHA_TAG}"

echo "==> Pushing ${LATEST_TAG}"
docker push "${LATEST_TAG}"

cat <<EOF

==> Done.
    Pushed: ${SHA_TAG}
            ${LATEST_TAG}

    On the deploy host, with .env populated:
        docker compose pull && docker compose up -d

    To pin to this exact build instead of :latest:
        IMAGE_TAG=${SHA} docker compose up -d

EOF
