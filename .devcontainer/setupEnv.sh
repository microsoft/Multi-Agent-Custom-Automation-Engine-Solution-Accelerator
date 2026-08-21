#!/bin/sh

echo "Pull latest code for the current branch"
git fetch
git pull

set -e 

echo "Setting up Backend..."
cd ./src/backend
uv sync --frozen
cd ../../

echo "Setting up Frontend..."
cd ./src/App
npm_install_start=$(date +%s)
npm install
npm_install_end=$(date +%s)
echo "npm install duration: $((npm_install_end-npm_install_start))s"
pip install -r requirements.txt
cd ../../

echo "Setting up MCP..."
cd ./src/mcp_server
uv sync --frozen
cd ../../

echo "Setup complete! 🎉"