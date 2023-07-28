# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os
from aws_cdk import aws_iam


class UtilsService:
    @staticmethod
    def root_dir():
        file_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(file_dir, ".."))

    @staticmethod
    def build_lambda_environment(
        stage: str,
        region: str,
        is_production: bool,
        nucleoni_store_api_storage_bucket: str,
        aurora_endpoint: str,
        memcached_endpoint: str,
    ):
        return {
            "STAGE": stage,
            "DEPLOYMENT_REGION": region,
            "NUCLEONI_STORE_API_STORAGE_BUCKET_NAME": nucleoni_store_api_storage_bucket,
            "AURORA_PASSWORD_SSM_PARAMETER": f"/infra/rds_password/{stage}",
            "AURORA_ENDPOINT": aurora_endpoint,
            "MEMCACHED_ENDPOINT": memcached_endpoint,
            "DEBUG": "False" if is_production else "True",
            "ENABLE_DEBUG_TOOLBAR": "False" if is_production else "True",
            "RSA_PRIVATE_KEY_ROOT": "/tmp",
        }

    @staticmethod
    def build_lambda_permissions():
        return [
            aws_iam.PolicyStatement(
                actions=[
                    "s3:*",
                ],
                resources=["*"],
            ),
            aws_iam.PolicyStatement(
                actions=[
                    "rds:*",
                ],
                resources=["*"],
            ),
            aws_iam.PolicyStatement(
                actions=[
                    "sqs:*",
                ],
                resources=["*"],
            ),
            aws_iam.PolicyStatement(
                actions=[
                    "ecr:*",
                ],
                resources=["*"],
            ),
            aws_iam.PolicyStatement(
                actions=[
                    "kms:*",
                ],
                resources=["*"],
            ),
            aws_iam.PolicyStatement(
                actions=[
                    "ssm:*",
                ],
                resources=["*"],
            ),
            aws_iam.PolicyStatement(
                actions=[
                    "ses:*",
                ],
                resources=["*"],
            ),
        ]
