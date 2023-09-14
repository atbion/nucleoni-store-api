# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os

from aws_cdk import (
    Stack,
    aws_certificatemanager,
    aws_route53,
    aws_ssm,
)
from constructs import Construct


class StoreApiUsCertificatesStack(Stack):
    nucleoni_store_api_certificate = None

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.stage = os.environ.get("STAGE", "dev")
        self.is_production = self.stage == "prod"
        self.nucleoni_store_api_certificate = None
        self.nucleoni_hosted_zone = None

        # Setup common resources
        self.setup_common_resources()
        # Setup Nucleoni Store Api Certificate
        self.setup_nucleoni_store_api_certificate()

    def setup_common_resources(self):
        self.nucleoni_hosted_zone = aws_route53.HostedZone.from_lookup(
            self,
            f"nucleoni-hosted-zone-{self.stage}",
            domain_name="nucleoni.com",
        )

    def setup_nucleoni_store_api_certificate(self):
        # Create Store Api Certificate
        self.nucleoni_store_api_certificate = aws_certificatemanager.Certificate(
            self,
            f"nucleoni-store-api-certificate-{self.stage}",
            domain_name="app.nucleoni.com",
            validation=aws_certificatemanager.CertificateValidation.from_dns(
                self.nucleoni_hosted_zone,
            ),
            subject_alternative_names=[
                "*.app.nucleoni.com",
            ],
        )
        aws_ssm.StringParameter(
            self,
            f"/infra/nucleoni-store-api-certificate-arn/{self.stage}",
            string_value=self.nucleoni_store_api_certificate.certificate_arn,
            parameter_name=f"/infra/nucleoni-store-api-certificate-arn/{self.stage}",
        )
