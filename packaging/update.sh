#!/bin/bash
# Out-of-process updater for usbip-node on Linux.
# Run by the node service when the user clicks Update. Do not run directly unless testing.
set -euo pipefail

REPO_DIR="${USBIP_NODE_UPDATE_REPO:-/opt/usbip-node}"
BRANCH="${USBIP_NODE_UPDATE_BRANCH:-main}"
STATE_DIR="${USBIP_NODE_STATE_DIR:-/var/lib/usbip-node}"
LOG_FILE="$STATE_DIR/update.log"
JSONL_FILE="$STATE_DIR/update.jsonl"

mkdir -p "$STATE_DIR"

log_json() {
    local level="$1"
    local stage="$2"
    local message="$3"
    local before="${4:-}"
    local after="${5:-}"
    local ts
    ts="$(date -Iseconds)"
    printf '{"ts":"%s","level":"%s","stage":"%s","message":"%s","commit_before":"%s","commit_after":"%s"}\n' \
        "$ts" "$level" "$stage" "$message" "$before" "$after" >> "$JSONL_FILE"
}

log_text() {
    echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"
}

log_text "Helper started; repo=$REPO_DIR branch=$BRANCH"
log_json "info" "fetching" "Out-of-process update helper started"

if [ ! -d "$REPO_DIR/.git" ]; then
    msg="No git checkout at $REPO_DIR"
    log_text "!! $msg"
    log_json "error" "error" "$msg"
    exit 1
fi

cd "$REPO_DIR"
before_commit="$(git rev-parse HEAD)"
log_text "==> Updating repo at $REPO_DIR (branch: $BRANCH)"

log_text "==> Tagging current commit as rollback point"
TAG="pre-update-$(date +%s)"
git tag "$TAG" || true

log_json "info" "fetching" "Tagging rollback point $TAG" "$before_commit"

log_text "==> Fetching origin"
if ! git fetch origin >> "$LOG_FILE" 2>&1; then
    log_json "error" "error" "git fetch origin failed"
    exit 1
fi

log_text "==> Updating to origin/$BRANCH"
if ! git reset --hard "origin/$BRANCH" >> "$LOG_FILE" 2>&1; then
    log_json "error" "error" "git reset --hard origin/$BRANCH failed"
    exit 1
fi

after_commit="$(git rev-parse HEAD)"
log_json "info" "pulling" "Repo reset to origin/$BRANCH" "$before_commit" "$after_commit"

log_text "==> Re-installing service"
export USBIP_NODE_UPDATE_BRANCH="$BRANCH"
if ! packaging/install-linux.sh >> "$LOG_FILE" 2>&1; then
    log_json "error" "error" "install-linux.sh failed"
    exit 1
fi

log_json "success" "restarting" "Re-install complete; service will restart" "$before_commit" "$after_commit"
log_text "==> Done. Service restart in progress."
