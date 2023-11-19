#!/usr/bin/env bash
virtualenv venv -p python3.9
. ./venv/bin/activate
pip install -r requirements_cdk.txt
curl -sSL https://install.python-poetry.org | python3 -
poetry install
