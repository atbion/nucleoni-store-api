#!/usr/bin/env bash
curl -sSL https://install.python-poetry.org | python3.9 -
poetry config virtualenvs.in-project true
poetry install
source .venv/bin/activate
pip install -r requirements_cdk.txt
