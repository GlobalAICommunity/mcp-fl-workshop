#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--accept-cli-license" || "$#" -ne 1 ]]; then
    printf '%s\n' \
        "Read the Foundry Local CLI license before installing:" \
        "https://github.com/microsoft/foundry-local/blob/main/LICENSE" \
        "Then run: bash docs/codespaces/setup.sh --accept-cli-license" >&2
    exit 2
fi

if [[ "$(uname -sm)" != "Linux x86_64" ]]; then
    echo "This workshop image supports Linux x86_64 only." >&2
    exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"
export VIRTUAL_ENV="/opt/workshop-venv"
export MCP_WORKSHOP_PYTHON="$VIRTUAL_ENV/bin/python"
export PATH="$VIRTUAL_ENV/bin:$PATH"
if [[ ! -x "$MCP_WORKSHOP_PYTHON" ]]; then
    echo "Workshop Python is missing at $MCP_WORKSHOP_PYTHON. Create or rebuild the Codespace with .devcontainer/devcontainer.json; do not install the Windows requirements-lock.txt." >&2
    exit 1
fi
"$MCP_WORKSHOP_PYTHON" scripts/verify_setup.py --skip-model

version="0.10.0"
archive="foundry-${version}-linux-x64.tar.gz"
checksum="bcad5aca68aafbe042d56d241e255fb4a8f90189d32a75f1657c3e06acedf323"
install_dir="$HOME/.local/share/foundry-cli/${version}"
binary="$install_dir/foundry-${version}-linux-x64/lib/foundry"

if [[ ! -x "$binary" ]]; then
    download_dir="$(mktemp -d)"
    trap 'rm -f "$download_dir/$archive"; rmdir "$download_dir"' EXIT
    curl --fail --location --silent --show-error --retry 3 \
        "https://github.com/microsoft/foundry-local/releases/download/cli-preview-${version}/${archive}" \
        --output "$download_dir/$archive"
    (cd "$download_dir" && printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check -)
    mkdir -p "$install_dir"
    tar -xzf "$download_dir/$archive" -C "$install_dir"
    chmod +x "$binary" "$(dirname "$binary")/foundrylocald"
fi

if [[ -e /usr/local/bin/foundry || -L /usr/local/bin/foundry ]]; then
    if [[ "$(readlink -f /usr/local/bin/foundry)" != "$binary" ]]; then
        echo "A different foundry installation exists at /usr/local/bin/foundry; remove or relocate it before setup." >&2
        exit 1
    fi
else
    sudo ln -s "$binary" /usr/local/bin/foundry
fi
foundry --version

echo "Downloading the SDK's CPU model cache and checking a structured tool call..."
"$MCP_WORKSHOP_PYTHON" scripts/prepare_vm.py
"$MCP_WORKSHOP_PYTHON" scripts/verify_setup.py
echo "Codespaces setup complete. Continue with docs/codespaces/README.md."
