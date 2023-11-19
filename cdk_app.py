#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os

import aws_cdk as cdk

from stacks.store_api_storage_bucket import StoreApiStorageBucketStack
from stacks.us_certificates import UsCertificatesStack
from stacks.store_api import StoreApiStack

stage = os.environ.get("STAGE", "dev")
env_eu = cdk.Environment(account="486592719971", region="eu-west-1")
env_us = cdk.Environment(account="486592719971", region="us-east-1")

app = cdk.App()

us_certificates_stack = UsCertificatesStack(
    app,
    f"nucleoni-store-api-us-cert-stack-{stage}",
    env=env_us,
)

landing_api_storage_bucket_stack = StoreApiStorageBucketStack(
    app,
    f"nucleoni-store-api-storage-bucket-{stage}",
    env=env_us,
)

nucleoni_store_api_ecs_service_stack = StoreApiStack(
    app,
    f"nucleoni-store-api-stack-{stage}",
    env=env_eu,
    store_api_storage_bucket=landing_api_storage_bucket_stack.store_api_storage_bucket,
    store_api_certificate=us_certificates_stack.store_api_certificate,
    cross_region_references=True,
)

app.synth()
