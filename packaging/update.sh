#!/bin/bash
# Out-of-process updater for usbip-node on Linux.
# Run by the node service when the user clicks Update. Do not run directly unless testing.
set -euo pipefail

REPO_DIR="/opt/usbip-node"
BRANCH="${USBIP_NODE_UPDATE_BRANCH:-main}"

if [ ! -d "$REPO_DIR/.git" ]; then
    echo "!! No git checkout at $REPO_DIR" >&2
    exit 1
fi

cd "$REPO_DIR"

echo "==> Tagging current commit as rollback point"
TAG="pre-update-$(date +%s)"
git tag "$TAG" || true

echo "==> Fetching origin"
git fetch origin

echo "==> Updating to origin/$BRANCH"
git reset --hard "origin/$BRANCH"

echo "==> Re-installing service"
export USBIP_NODE_UPDATE_BRANCH="$BRANCH"
packaging/install-linux.sh
