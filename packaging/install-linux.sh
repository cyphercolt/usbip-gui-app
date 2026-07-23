#!/usr/bin/env bash
# Install usbip-node as a systemd service on Linux / Raspberry Pi.
# Run as root:  sudo packaging/install-linux.sh
#
# Result: the node runs on boot at http://<this-machine-ip>:4820, USB/IP works with no sudo prompts.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX=/opt/usbip-node
PORT="${USBIP_NODE_PORT:-4820}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo $0" >&2
  exit 1
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

echo "==> Installing systemd service"
sed "s/USBIP_NODE_PORT=4820/USBIP_NODE_PORT=$PORT/" "$REPO_DIR/packaging/usbip-node.service" \
  > /etc/systemd/system/usbip-node.service
systemctl daemon-reload
systemctl enable --now usbip-node.service

IP=$(hostname -I | awk '{print $1}')
echo
echo "==> Done. usbip-node is running."
echo "    Open from any phone/PC on the LAN:  http://$IP:$PORT"
echo "    Logs:    journalctl -u usbip-node -f"
echo "    Status:  systemctl status usbip-node"
