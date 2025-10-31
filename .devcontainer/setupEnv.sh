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
cd ./src/frontend
npm install
pip install -r requirements.txt
cd ../../

echo "Setting up MCP..."
cd ./src/mcp_server
uv sync --frozen
cd ../../

echo "Setup complete! 🎉"