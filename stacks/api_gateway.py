# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os

from aws_cdk import (
    Duration,
    Stack,
    aws_apigateway,
    aws_certificatemanager,
    aws_ec2,
    aws_iam,
    aws_lambda,
    aws_route53,
    aws_route53_targets,
    aws_s3,
    aws_ssm,
)
from constructs import Construct

from stacks.utils import UtilsService


class ApiGatewayStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        nucleoni_store_api_storage_bucket: aws_s3.Bucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.vpc = None
        self.stage = os.environ.get("STAGE", "dev")
        self.is_production = self.stage == "prod"
        self.nucleoni_hosted_zone = None
        self.nucleoni_store_api_gateway_lambda_handler = None
        self.nucleoni_store_api_gateway = None
        self.nucleoni_store_api_gateway_certificate = None
        self.nucleoni_store_api_storage_bucket = nucleoni_store_api_storage_bucket
        self.memcached_endpoint = aws_ssm.StringParameter.value_from_lookup(
            self,
            f"/infra/cache_endpoint/{self.stage}",
        )

        # Setup common resources
        self.setup_common_resources()
        # Setup Nucleoni Store API Lambda Handler
        self.setup_nucleoni_store_api_gateway_lambda_handler()
        # Setup API Gateway
        self.setup_api_gateway()

    def setup_common_resources(self):
        vpc_id = aws_ssm.StringParameter.value_from_lookup(
            self, f"/infra/vpc-id/{self.stage}"
        )
        self.vpc = aws_ec2.Vpc.from_lookup(self, f"vpc-{self.stage}", vpc_id=vpc_id)
        self.nucleoni_hosted_zone = aws_route53.HostedZone.from_lookup(
            self,
            f"nucleoni-hosted-zone-{self.stage}",
            domain_name="nucleoni.com",
        )

    def setup_nucleoni_store_api_gateway_lambda_handler(self):
        lambda_env = UtilsService.build_lambda_environment(
            stage=self.stage,
            region=self.region,
            is_production=self.is_production,
            nucleoni_store_api_storage_bucket=self.nucleoni_store_api_storage_bucket.bucket_name,
            aurora_endpoint=aws_ssm.StringParameter.value_from_lookup(
                self,
                f"/infra/rds_endpoint/dev",  # For now, we are using dev endpoint
            ),
            memcached_endpoint=self.memcached_endpoint,
        )
        self.nucleoni_store_api_gateway_lambda_handler = aws_lambda.DockerImageFunction(
            self,
            f"nucleoni-store-api-gateway-lambda-handler-{self.stage}",
            code=aws_lambda.DockerImageCode.from_image_asset(
                directory=UtilsService.root_dir(),
                file="DockerfileNucleoni"
            ),
            vpc=self.vpc,
            timeout=Duration.seconds(30),
            vpc_subnets=aws_ec2.SubnetSelection(subnets=self.vpc.private_subnets),
            environment=lambda_env,
            memory_size=1024,
        )
        self.nucleoni_store_api_gateway_lambda_handler.role.attach_inline_policy(
            aws_iam.Policy(
                self,
                f"nucleoni-store-api-lambda-handler-policy-{self.stage}",
                statements=UtilsService.build_lambda_permissions(),
            )
        )

        aws_ssm.StringParameter(
            self,
            f"/infra/nucleoni-store-api-gateway-lambda-handler-{self.stage}",
            parameter_name=f"/infra/nucleoni-store-api-gateway-lambda-handler-arn/{self.stage}",
            string_value=self.nucleoni_store_api_gateway_lambda_handler.function_arn,
        )

    def setup_api_gateway(self):
        version = self.nucleoni_store_api_gateway_lambda_handler.current_version
        # Define the REST API
        self.nucleoni_store_api_gateway = aws_apigateway.RestApi(
            self,
            f"nucleoni-store-api-gateway-{self.stage}",
            rest_api_name=f"nucleoni-store-api-gateway-{self.stage}",
            disable_execute_api_endpoint=True,
            deploy=False,
        )

        # Define a resource for /v1
        stage_root_resource = self.nucleoni_store_api_gateway.root.add_resource("v1")
        proxy_resource_any_method = stage_root_resource.add_proxy(
            default_integration=aws_apigateway.AwsIntegration(
                service="lambda",
                proxy=True,
                path=f"2015-03-31/functions/{self.nucleoni_store_api_gateway_lambda_handler.function_arn}:${{stageVariables.lambdaAlias}}/invocations",
            ),
            any_method=True,
        )
        # Define stage specific resources
        alias = aws_lambda.Alias(
            self,
            f"nucleoni-store-api-gateway-stage-alias-{self.stage}",
            alias_name=f"{self.stage}",
            version=version,
        )

        deployment = aws_apigateway.Deployment(
            self,
            f"nucleoni-store-api-gateway-deployment-{self.stage}",
            api=self.nucleoni_store_api_gateway,
        )

        stage = aws_apigateway.Stage(
            self,
            f"nucleoni-store-api-gateway-stage-{self.stage}",
            deployment=deployment,
            stage_name=f"{self.stage}",
            variables={"lambdaAlias": alias.alias_name},
        )

        alias.add_permission(
            f"nucleoni-store-api-gateway-alias-permission-{self.stage}",
            principal=aws_iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.nucleoni_store_api_gateway.arn_for_execute_api(
                method=proxy_resource_any_method.any_method.http_method,
                stage=stage.stage_name,
            ),
        )

        # Create custom domain name
        self.nucleoni_store_api_gateway_certificate = aws_certificatemanager.Certificate(
            self,
            f"nucleoni-store-api-gateway-certificate-{self.stage}",
            domain_name="store-api.nucleoni.com",
            validation=aws_certificatemanager.CertificateValidation.from_dns(
                self.nucleoni_hosted_zone,
            ),
            subject_alternative_names=[
                "*.store-api.nucleoni.com",
            ],
        )

        domain_name_str = (
            "store-api.nucleoni.com"
            if self.is_production
            else f"{self.stage}.store-api.nucleoni.com"
        )

        domain_name = aws_apigateway.DomainName(
            self,
            f"nucleoni-store-api-gateway-domain-name-{self.stage}",
            domain_name=domain_name_str,
            certificate=self.nucleoni_store_api_gateway_certificate,
            endpoint_type=aws_apigateway.EndpointType.REGIONAL,
        )

        aws_apigateway.BasePathMapping(
            self,
            f"nucleoni-store-api-gateway-base-path-mapping-{self.stage}",
            domain_name=domain_name,
            rest_api=self.nucleoni_store_api_gateway,
            stage=stage,
        )

        aws_route53.ARecord(
            self,
            f"nucleoni-store-api-gateway-domain-record-{self.stage}",
            target=aws_route53.RecordTarget.from_alias(
                aws_route53_targets.ApiGatewayDomain(domain_name)
            ),
            zone=self.nucleoni_hosted_zone,
            record_name=domain_name_str,
            ttl=Duration.seconds(300),
        )
