#!/bin/bash
# Python Environment Bundler for VS Code Extension
# This script creates a bundled Python environment for the extension

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_DIR="$SCRIPT_DIR/python"
PYTHON_VERSION="3.11.8"

echo "=== Mini KI Tools Python Bundler ==="
echo "Creating bundled Python environment at: $PYTHON_DIR"

# Create Python directory
mkdir -p "$PYTHON_DIR"

# Download and extract Python (if not already present)
if [ ! -f "$PYTHON_DIR/python3" ]; then
    echo "Downloading Python $PYTHON_VERSION..."
    
    # Detect OS and architecture
    OS=$(uname -s)
    ARCH=$(uname -m)
    
    case "$OS" in
        Linux)
            if [ "$ARCH" = "x86_64" ]; then
                PYTHON_TGZ="https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_VERSION}%2B20240224/python-${PYTHON_VERSION}+20240224-x86_64-unknown-linux-gnu.tar.gz"
            elif [ "$ARCH" = "aarch64" ]; then
                PYTHON_TGZ="https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_VERSION}%2B20240224/python-${PYTHON_VERSION}+20240224-aarch64-unknown-linux-gnu.tar.gz"
            fi
            ;;
        Darwin)
            if [ "$ARCH" = "x86_64" ]; then
                PYTHON_TGZ="https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_VERSION}%2B20240224/python-${PYTHON_VERSION}+20240224-x86_64-apple-darwin.tar.gz"
            elif [ "$ARCH" = "arm64" ]; then
                PYTHON_TGZ="https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_VERSION}%2B20240224/python-${PYTHON_VERSION}+20240224-aarch64-apple-darwin.tar.gz"
            fi
            ;;
        *)
            echo "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    
    echo "Downloading from: $PYTHON_TGZ"
    curl -L -o "$PYTHON_DIR/python.tar.gz" "$PYTHON_TGZ"
    
    echo "Extracting Python..."
    tar -xzf "$PYTHON_DIR/python.tar.gz" -C "$PYTHON_DIR" --strip-components=1
    
    rm "$PYTHON_DIR/python.tar.gz"
fi

# Verify Python installation
echo "Verifying Python installation..."
"$PYTHON_DIR/python3" --version

# Create virtual environment with bundled Python
echo "Creating virtual environment..."
cd "$SCRIPT_DIR"
"$PYTHON_DIR/python3" -m venv "$PYTHON_DIR/venv"

# Activate venv and install dependencies
echo "Installing dependencies..."
source "$PYTHON_DIR/venv/bin/activate"

# Install minimal dependencies for the agent
pip install --quiet --no-cache-dir \
    requests==2.31.0 \
    pydantic==2.5.0 \
    pyyaml==6.0 \
    sseclient-py==1.8.2 \
    aiohttp==3.9.0 \
    watchdog==3.0.0

# Copy Python source files
echo "Copying Python source files..."
mkdir -p "$PYTHON_DIR/src"
cp -r "$SCRIPT_DIR/../src/"* "$PYTHON_DIR/src/"

# Create __init__.py files
touch "$PYTHON_DIR/src/__init__.py"

echo "=== Python bundling complete ==="
echo "Python environment ready at: $PYTHON_DIR"