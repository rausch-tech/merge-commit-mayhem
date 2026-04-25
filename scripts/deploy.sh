#!/usr/bin/env bash
# Deploy MCM to the EC2 instance.
#
# Usage (local):
#   ./scripts/deploy.sh
#   EC2_HOST=3.78.184.97 EC2_USER=ubuntu ./scripts/deploy.sh
#
# Usage (CI): same — the workflow exports the right env vars.

set -euo pipefail

EC2_HOST="${EC2_HOST:-3.78.184.97}"
EC2_USER="${EC2_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/mcm-game-server.pem}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/opt/mcm}"
SERVICE_NAME="${SERVICE_NAME:-mcm-server.service}"

if [[ ! -f "$SSH_KEY" ]]; then
    echo "ERROR: SSH key not found at $SSH_KEY"
    echo "Either install the key there or set SSH_KEY=path/to/key"
    exit 1
fi

# Build tarball from current working tree.
TARBALL=$(mktemp -t mcm-deploy-XXXXXX.tgz)
trap 'rm -f "$TARBALL"' EXIT

echo ">>> Building deploy tarball..."
tar --exclude='.git' \
    --exclude='.venv' \
    --exclude='.worktrees' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='node_modules' \
    --exclude='uv.lock' \
    -czf "$TARBALL" \
    pyproject.toml app/ static/ images/ sounds/ maps/ tests/ README.md

SIZE=$(stat -c %s "$TARBALL")
echo ">>> Tarball: $TARBALL ($SIZE bytes)"

echo ">>> Uploading to ${EC2_USER}@${EC2_HOST}..."
scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$TARBALL" "${EC2_USER}@${EC2_HOST}:/tmp/mcm-deploy.tgz"

echo ">>> Extracting + restarting on remote..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "${EC2_USER}@${EC2_HOST}" bash -s <<EOF
set -euo pipefail
sudo tar -xzf /tmp/mcm-deploy.tgz -C "$REMOTE_APP_DIR"
sudo chown -R ubuntu:ubuntu "$REMOTE_APP_DIR"
cd "$REMOTE_APP_DIR"
sudo -u ubuntu bash -lc 'export PATH="\$HOME/.local/bin:\$PATH" && uv sync --no-dev'
sudo systemctl restart "$SERVICE_NAME"
sleep 2
sudo systemctl is-active "$SERVICE_NAME"
echo ">>> Deploy successful"
EOF

echo ">>> Done."
