#!/usr/bin/env bash
set -eou pipefail

mkdir -p dist
rm -rf dist/*

#python
cp -f requirements.txt dist
cp -f *.py dist

#node
npm_install_start=$(date +%s)
npm install
npm_install_end=$(date +%s)
echo "npm install duration: $((npm_install_end-npm_install_start))s"
npm run build
cp -rf build dist