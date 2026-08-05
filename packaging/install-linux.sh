#!/usr/bin/env bash
# Install usbip-node as a systemd service on Linux / Raspberry Pi.
# Run as root:  sudo packaging/install-linux.sh
#
# Result: the node runs on boot at http://<this-machine-ip>:4820, USB/IP works with no sudo prompts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX=/opt/usbip-node
PORT="${USBIP_NODE_PORT:-4820}"
UPDATE_BRANCH="${USBIP_NODE_UPDATE_BRANCH:-main}"
UPSTREAM_URL="${USBIP_NODE_REPO_URL:-https://github.com/cyphercolt/usbip-gui-app.git}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo $0" >&2
  exit 1
fi

# Pick the git checkout to install from. Priority:
#   1. USBIP_NODE_UPDATE_REPO env override (power users)
#   2. The directory this script is inside (normal "git clone + run install")
#   3. /opt/usbip-node if it's already a git checkout (re-run install to update)
#   4. Clone the public repo into /opt/usbip-node (release tarball / curl pipe)
if [ -n "${USBIP_NODE_UPDATE_REPO:-}" ]; then
  REPO_DIR="$(cd "$USBIP_NODE_UPDATE_REPO" && pwd)"
  if [ ! -d "$REPO_DIR/.git" ]; then
    echo "!! USBIP_NODE_UPDATE_REPO ($USBIP_NODE_UPDATE_REPO) is not a git checkout" >&2
    exit 1
  fi
  echo "==> Installing from override repo: $REPO_DIR"
elif [ -d "$SCRIPT_DIR/../.git" ]; then
  REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
  echo "==> Installing from current directory: $REPO_DIR"
elif [ -d "$PREFIX/.git" ]; then
  REPO_DIR="$PREFIX"
  echo "==> Updating existing install at $PREFIX"
else
  echo "==> No local git checkout found; cloning $UPSTREAM_URL"
  rm -rf "$PREFIX"
  git clone --branch "$UPDATE_BRANCH" "$UPSTREAM_URL" "$PREFIX"
  REPO_DIR="$PREFIX"
fi

echo "==> Installing usbip + Python"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y usbip python3-venv python3-pip >/dev/null
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y usbip python3 python3-pip >/dev/null || dnf install -y kernel-modules-extra usbip >/dev/null || true
else
  echo "!! Unknown package manager — install 'usbip' and python3-venv yourself, then re-run." >&2
fi

echo "==> Enabling USB/IP kernel modules"
printf 'vhci_hcd\nusbip_host\n' > /etc/modules-load.d/usbip.conf
modprobe vhci_hcd 2>/dev/null || true
modprobe usbip_host 2>/dev/null || true

echo "==> Building the web UI (if needed)"
if [ ! -f "$REPO_DIR/web/dist/index.html" ]; then
  if command -v npm >/dev/null 2>&1; then
    ( cd "$REPO_DIR/web" && npm install --no-audit --no-fund && npm run build )
  else
    echo "!! web/dist missing and npm not found. Build it on your dev machine first:" >&2
    echo "     (cd web && npm install && npm run build)" >&2
    exit 1
  fi
fi

echo "==> Installing to $PREFIX"
mkdir -p "$PREFIX"
python3 -m venv "$PREFIX/.venv"
"$PREFIX/.venv/bin/pip" install --quiet --upgrade pip
"$PREFIX/.venv/bin/pip" install --quiet "$REPO_DIR/node"
rm -rf "$PREFIX/web"
cp -r "$REPO_DIR/web/dist" "$PREFIX/web"
cp "$REPO_DIR/packaging/update.sh" "$PREFIX/update.sh"
chmod +x "$PREFIX/update.sh"

echo "==> Installing systemd service"
SERVICE_FILE=$(mktemp)
sed -e "s/USBIP_NODE_PORT=4820/USBIP_NODE_PORT=$PORT/" \
    -e "s|#USBIP_NODE_UPDATE_BRANCH=main|USBIP_NODE_UPDATE_BRANCH=$UPDATE_BRANCH|" \
    "$REPO_DIR/packaging/usbip-node.service" > "$SERVICE_FILE"
# Tell the running service where the real git checkout lives, unless it's the default /opt path.
if [ "$REPO_DIR" != "$PREFIX" ]; then
  sed -i "s|#USBIP_NODE_UPDATE_REPO=|USBIP_NODE_UPDATE_REPO=$REPO_DIR|" "$SERVICE_FILE"
fi
mv "$SERVICE_FILE" /etc/systemd/system/usbip-node.service
chmod 644 /etc/systemd/system/usbip-node.service
systemctl daemon-reload
systemctl enable usbip-node.service
systemctl restart usbip-node.service   # restart so re-running this script also UPDATES a live node

IP=$(hostname -I | awk '{print $1}')
echo
echo "==> Done. usbip-node is running."
echo "    Open from any phone/PC on the LAN:  http://$IP:$PORT"
echo "    Logs:    journalctl -u usbip-node -f"
echo "    Status:  systemctl status usbip-node"
