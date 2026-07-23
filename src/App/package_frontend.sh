#!/usr/bin/env bash
set -eou pipefail

mkdir -p dist
rm -rf dist/*

#python
cp -f requirements.txt dist
cp -f *.py dist

#node
npm install
npm run build
cp -rf build dist