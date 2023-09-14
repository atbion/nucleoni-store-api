#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os

import aws_cdk as cdk

from stacks.store_api import NucleoniStoreApiStack
from stacks.api_storage_bucket import ApiStorageBucketStack
from stacks.us_certificates import StoreApiUsCertificatesStack

STAGE = os.environ.get("STAGE", "dev")
env_eu = cdk.Environment(account="486592719971", region="eu-west-1")
env_us = cdk.Environment(account="486592719971", region="us-east-1")

app = cdk.App()

us_certificates_stack = StoreApiUsCertificatesStack(
    app,
    f"nucleoni-store-api-us-certificates-stack-{STAGE}",
    env=env_us,
)

api_storage_bucket_stack = ApiStorageBucketStack(
    app,
    f"nucleoni-store-api-storage-bucket-{STAGE}",
    env=env_us,
)

api_gateway_stack = NucleoniStoreApiStack(
    app,
    f"nucleoni-store-api-stack-{STAGE}",
    env=env_eu,
    cross_region_references=True,
    nucleoni_store_api_storage_bucket=api_storage_bucket_stack.nucleoni_store_api_storage_bucket,
    nucleoni_store_api_certificate=us_certificates_stack.nucleoni_store_api_certificate,
)

app.synth()
