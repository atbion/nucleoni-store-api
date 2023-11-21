# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os
from aws_cdk import aws_iam
from aws_cdk import aws_ssm


class UtilsService:
    @staticmethod
    def root_dir():
        file_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(file_dir, ".."))

    @staticmethod
    def build_store_api_environment(
        stage: str,
        region: str,
        is_production: bool,
        store_api_storage_bucket: str,
        aurora_endpoint: str,
    ):
        return {
            "STAGE": stage,
            "DEPLOYMENT_REGION": region,
            "STORE_API_STORAGE_BUCKET_NAME": store_api_storage_bucket,
            "DJANGO_DEBUG": "FALSE" if is_production else "TRUE",
            "AURORA_PASSWORD_SSM_PARAMETER": "/infra/rds_password/cluster-1",
            "NUCLEONI_ROOT_PASSWORD_SSM_PARAMETER": f"/infra/nucleoni-root/password/{stage}",
            "AURORA_ENDPOINT": aurora_endpoint,
            "AWS_STATIC_CUSTOM_DOMAIN": os.environ.get("AWS_MEDIA_BUCKET_NAME"),
            "AWS_STORAGE_BUCKET_NAME": os.environ.get("AWS_MEDIA_BUCKET_NAME"),
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

    @staticmethod
    def get_ssm_parameter_arn(construct, parameter_name: str):
        value = aws_ssm.StringParameter.value_from_lookup(
            construct, parameter_name
        )
        if 'dummy-value' in value:
            value = 'arn:aws:service:eu-central-1:123456789012:entity/dummy-value'
        return value
