#!/bin/bash

cd ./src/backend
uv add -r requirements.txt

cd ../frontend
uv add -r requirements.txt

cd ..







# pip install --upgrade pip


# (cd ./src/frontend; pip install -r requirements.txt)


# (cd ./src/backend; pip install -r requirements.txt)


