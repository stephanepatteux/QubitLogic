#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# QubitLogic — local dev environment setup
# Run from repo root:  bash scripts/setup-dev.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

HUGO_VERSION="0.162.1"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"

echo "==> Initializing git submodules..."
git submodule update --init --recursive

install_hugo() {
  local arch os tarball url target_dir
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"

  case "$arch" in
    x86_64|amd64) arch="amd64" ;;
    aarch64|arm64) arch="arm64" ;;
    *)
      echo "Unsupported architecture: $arch" >&2
      exit 1
      ;;
  esac

  tarball="hugo_extended_${HUGO_VERSION}_${os}-${arch}.tar.gz"
  url="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/${tarball}"

  if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    target_dir="/usr/local/bin"
    sudo mkdir -p "$target_dir"
    curl -fsSL "$url" -o "/tmp/${tarball}"
    sudo tar -xzf "/tmp/${tarball}" -C "$target_dir" hugo
    rm -f "/tmp/${tarball}"
  else
    target_dir="${HOME}/.local/bin"
    mkdir -p "$target_dir"
    curl -fsSL "$url" -o "/tmp/${tarball}"
    tar -xzf "/tmp/${tarball}" -C "$target_dir" hugo
    rm -f "/tmp/${tarball}"
    export PATH="${target_dir}:${PATH}"
    if ! grep -qs "${target_dir}" "${HOME}/.bashrc" 2>/dev/null; then
      echo "export PATH=\"${target_dir}:\$PATH\"" >> "${HOME}/.bashrc"
      echo "Added ${target_dir} to PATH in ~/.bashrc"
    fi
  fi
}

need_hugo=false
if ! command -v hugo >/dev/null 2>&1; then
  need_hugo=true
elif ! hugo version | grep -q "v${HUGO_VERSION}"; then
  echo "Found $(hugo version), but need v${HUGO_VERSION}"
  need_hugo=true
fi

if [ "$need_hugo" = true ]; then
  echo "==> Installing Hugo Extended v${HUGO_VERSION}..."
  install_hugo
else
  echo "==> Hugo $(hugo version | awk '{print $2}') already installed"
fi

echo "==> Installing Python dependencies..."
if ! python3 -c "import PIL" 2>/dev/null; then
  python3 -m pip install --user Pillow
else
  echo "Pillow already installed"
fi

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  hugo server -D          # preview at http://localhost:1313"
echo "  hugo --minify           # production build → public/"

if [ "${1:-}" = "--verify" ]; then
  echo ""
  echo "==> Verifying build..."
  python3 scripts/generate_cover_images.py
  python3 scripts/generate_og_images.py
  hugo --minify
  echo "Build OK."
fi
