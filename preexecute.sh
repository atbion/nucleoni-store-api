#!/usr/bin/env bash
virtualenv venv -p python3.9
. ./venv/bin/activate
pip install -r requirements_dev.txt
