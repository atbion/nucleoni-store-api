#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os

import aws_cdk as cdk

from stacks.api_gateway import ApiGatewayStack
from stacks.api_storage_bucket import ApiStorageBucketStack

STAGE = os.environ.get("STAGE", "dev")
env_eu = cdk.Environment(account="486592719971", region="eu-west-1")
env_us = cdk.Environment(account="486592719971", region="us-east-1")

app = cdk.App()

api_storage_bucket_stack = ApiStorageBucketStack(
    app,
    f"nucleoni-store-api-storage-bucket-{STAGE}",
    env=env_us,
    cross_region_references=True,
)

api_gateway_stack = ApiGatewayStack(
    app,
    f"nucleoni-store-api-stack-{STAGE}",
    env=env_eu,
    cross_region_references=True,
    nucleoni_store_api_storage_bucket=api_storage_bucket_stack.nucleoni_store_api_storage_bucket,
)

app.synth()
