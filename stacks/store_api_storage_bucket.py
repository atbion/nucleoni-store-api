# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_certificatemanager,
    aws_cloudfront,
    aws_cloudfront_origins,
    aws_route53,
    aws_route53_targets,
    aws_s3,
    aws_ssm,
)
from constructs import Construct


class StoreApiStorageBucketStack(Stack):
    store_api_storage_bucket = None

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.stage = os.environ.get("STAGE", "dev")
        self.is_production = self.stage == "prod"
        self.store_api_storage_bucket = None
        self.store_api_cloud_front_distribution = None
        self.hosted_zone = None

        # Setup common resources
        self.setup_common_resources()
        # Setup Nucleoni API Storage Bucket
        self.setup_store_api_storage_bucket()

    def setup_common_resources(self):
        self.hosted_zone = aws_route53.HostedZone.from_lookup(
            self,
            f"nucleoni-hosted-zone-{self.stage}",
            domain_name="nucleoni.com",
        )

    def setup_store_api_storage_bucket(self):
        # Create CloudFront Certificate
        cloud_front_certificate = aws_certificatemanager.Certificate(
            self,
            f"store-api-assets-cloud-front-certificate-{self.stage}",
            domain_name="store-api-assets.nucleoni.com",
            validation=aws_certificatemanager.CertificateValidation.from_dns(
                self.hosted_zone
            ),
            subject_alternative_names=[
                "*.store-api-assets.nucleoni.com",
            ],
        )
        # Create store API Storage Bucket Name
        store_api_storage_bucket_name = (
            f"store-api-assets.nucleoni.com"
            if self.is_production
            else f"{self.stage}.store-api-assets.nucleoni.com"
        )
        # Create store API Storage Bucket
        self.store_api_storage_bucket = aws_s3.Bucket(
            self,
            f"store-api-storage-bucket-{self.stage}",
            bucket_name=store_api_storage_bucket_name,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            public_read_access=False,
        )
        self.store_api_cloud_front_distribution = aws_cloudfront.Distribution(
            self,
            f"store-api-cloud-front-distribution-{self.stage}",
            default_behavior=aws_cloudfront.BehaviorOptions(
                origin=aws_cloudfront_origins.S3Origin(self.store_api_storage_bucket)
            ),
            domain_names=[self.store_api_storage_bucket.bucket_name],
            certificate=cloud_front_certificate,
        )

        aws_ssm.StringParameter(
            self,
            f"/infra/store-api-storage-bucket-name/{self.stage}",
            string_value=self.store_api_storage_bucket.bucket_name,
        )

        aws_ssm.StringParameter(
            self,
            f"/infra/store-api-storage-bucket-arn/{self.stage}",
            string_value=self.store_api_storage_bucket.bucket_arn,
        )

        aws_route53.ARecord(
            self,
            f"store-api-cloud-front-distribution-record-{self.stage}",
            target=aws_route53.RecordTarget.from_alias(
                aws_route53_targets.CloudFrontTarget(
                    self.store_api_cloud_front_distribution
                )
            ),
            zone=self.hosted_zone,
            record_name=store_api_storage_bucket_name,
            ttl=Duration.seconds(300),
        )
