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
)
from constructs import Construct


class UsCertificatesStack(Stack):
    store_api_certificate = None

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.stage = os.environ.get("STAGE", "dev")
        self.is_production = self.stage == "prod"
        self.store_api_certificate = None
        self.hosted_zone = None

        # Setup common resources
        self.setup_common_resources()
        # Setup Nucleoni API Storage Bucket
        self.setup_nucleoni_store_api_certificate()

    def setup_common_resources(self):
        self.hosted_zone = aws_route53.HostedZone.from_lookup(
            self,
            f"hosted-zone-{self.stage}",
            domain_name="nucleoni.com",
        )

    def setup_nucleoni_store_api_certificate(self):
        # Create CloudFront Certificate
        self.store_api_certificate = aws_certificatemanager.Certificate(
            self,
            f"store-api-certificate-{self.stage}",
            domain_name="store-api.nucleoni.com",
            validation=aws_certificatemanager.CertificateValidation.from_dns(
                self.hosted_zone,
            ),
            subject_alternative_names=[
                "*.store-api.nucleoni.com",
            ],
        )
