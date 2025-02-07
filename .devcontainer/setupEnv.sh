#!/bin/bash

pip install --upgrade pip


(cd ./src/frontend; pip install -r requirements.txt)

(cd ./src/backend; pip install -r requirements.txt)
