# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os

from aws_cdk import (Duration, RemovalPolicy, Stack, aws_certificatemanager,
                     aws_cloudfront, aws_cloudfront_origins, aws_dynamodb,
                     aws_ec2, aws_ecs, aws_elasticloadbalancingv2, aws_iam,
                     aws_lambda, aws_logs, aws_route53, aws_route53_targets,
                     aws_s3, aws_sqs, aws_ssm, aws_stepfunctions)
from constructs import Construct

from stacks.utils import UtilsService


class StoreApiStack(Stack):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            store_api_storage_bucket: aws_s3.Bucket,
            store_api_certificate: aws_certificatemanager.Certificate,
            **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.stage = os.environ.get("STAGE", "dev")
        self.is_production = self.stage == "prod"
        self.store_api_certificate = store_api_certificate
        self.store_api_storage_bucket = store_api_storage_bucket

        self.vpc = None
        self.hosted_zone = None
        self.store_api_ecs_service = None
        self.store_api_cloud_front_distribution = None

        # Setup common resources
        self.setup_common_resources()
        # Setup ECS Service
        self.setup_store_api_ecs_service()
        # Setup CloudFront Distribution
        self.setup_store_api_cloud_front_distribution()

    def setup_common_resources(self):
        vpc_id = aws_ssm.StringParameter.value_from_lookup(
            self, "/infra/vpc-id/vpc-atbion"
        )
        self.vpc = aws_ec2.Vpc.from_lookup(self, f"vpc-{self.stage}", vpc_id=vpc_id)
        self.hosted_zone = aws_route53.HostedZone.from_lookup(
            self,
            f"hosted-zone-{self.stage}",
            domain_name="nucleoni.com",
        )

    def setup_store_api_ecs_service(self):
        ecs_cluster = aws_ecs.Cluster.from_cluster_attributes(
            self,
            f"common-ecs-cluster",
            cluster_name=f"common-ecs-cluster",
            vpc=self.vpc,
        )

        # Create Task Definition
        task_definition = aws_ecs.FargateTaskDefinition(
            self, f"store-api-ecs-task-{self.stage}"
        )

        task_definition.add_to_task_role_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "ssm:*",
                ],
                resources=[
                    "*",
                ],
                effect=aws_iam.Effect.ALLOW,
            )
        )

        task_definition_log_group = aws_logs.LogGroup(
            self,
            f"store-api-task-group-{self.stage}",
            log_group_name=f"store-api-task-group-{self.stage}",
            removal_policy=RemovalPolicy.RETAIN,
            retention=aws_logs.RetentionDays.THREE_MONTHS,
        )

        container = task_definition.add_container(
            f"store-api-container-{self.stage}",
            image=aws_ecs.ContainerImage.from_asset(
                build_args={
                    "AWS_MEDIA_BUCKET_NAME": os.environ.get("AWS_MEDIA_BUCKET_NAME"),
                },
                directory=UtilsService.root_dir(),
                file="Dockerfile",
            ),
            cpu=256,
            memory_limit_mib=256,
            logging=aws_ecs.LogDriver.aws_logs(
                stream_prefix=f"store-api-{self.stage}",
                log_group=task_definition_log_group,
            ),
            environment=UtilsService.build_store_api_environment(
                stage=self.stage,
                region=self.region,
                is_production=self.is_production,
                store_api_storage_bucket=self.store_api_storage_bucket.bucket_name,
                aurora_endpoint=aws_ssm.StringParameter.value_from_lookup(
                    self,
                    f"/infra/rds_endpoint/cluster-1",
                ),
            ),
        )

        port_mapping = aws_ecs.PortMapping(
            container_port=8000, protocol=aws_ecs.Protocol.TCP
        )

        container.add_port_mappings(port_mapping)

        # Create Service
        self.store_api_ecs_service = aws_ecs.FargateService(
            self,
            f"nucleoni-store-api-service-{self.stage}",
            service_name=f"nucleoni-store-api-service-{self.stage}",
            cluster=ecs_cluster,
            task_definition=task_definition,
            vpc_subnets=aws_ec2.SubnetSelection(
                subnet_type=aws_ec2.SubnetType.PUBLIC,
            ),
            assign_public_ip=True,
            desired_count=1,
            circuit_breaker=aws_ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100,
            max_healthy_percent=200,
        )

        task_scaling = self.store_api_ecs_service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=2,
        )

        task_scaling.scale_on_cpu_utilization(
            f"nucleoni-store-api-service-cpu-scaling-{self.stage}",
            target_utilization_percent=85,
        )

        listener = aws_elasticloadbalancingv2.ApplicationListener.from_lookup(
            self,
            f"nucleoni-common-alb-listener-{self.stage}",
            listener_arn=aws_ssm.StringParameter.value_from_lookup(
                self,
                "/infra/common-alb-listener-443-arn",
            ),
            load_balancer_arn=aws_ssm.StringParameter.value_from_lookup(
                self,
                f"/infra/common-alb-arn",
            ),
        )

        target_group = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            f"nucleoni-store-api-alb-tg-{self.stage}",
            target_group_name=f"nucleoni-store-api-alb-tg-{self.stage}",
            port=80,
            targets=[
                self.store_api_ecs_service.load_balancer_target(
                    container_name=container.container_name,
                    container_port=port_mapping.container_port,
                ),
            ],
            vpc=self.vpc,
            health_check=aws_elasticloadbalancingv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
                healthy_http_codes="200",
            ),
        )

        aws_elasticloadbalancingv2.ApplicationListenerRule(
            self,
            id=f"nucleoni-store-api-listener-rule-{self.stage}",
            conditions=[
                aws_elasticloadbalancingv2.ListenerCondition.http_header(
                    name="x-atbion-app",
                    values=[
                        f"nucleoni-store-api-{self.stage}",
                    ],
                )
            ],
            priority=15 if self.stage == "dev" else 16 if self.stage == "qa" else 17 if self.stage == "homo" else 18,
            listener=listener,
            target_groups=[target_group],
        )

    def setup_store_api_cloud_front_distribution(self):
        self.store_api_cloud_front_distribution = aws_cloudfront.Distribution(
            self,
            f"nucleoni-store-api-cloud-front-distribution",
            default_behavior=aws_cloudfront.BehaviorOptions(
                origin=aws_cloudfront_origins.HttpOrigin(
                    domain_name="alb.atbion.com",
                    protocol_policy=aws_cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    custom_headers={
                        "x-atbion-app": f"nucleoni-store-api-{self.stage}",
                    },
                    origin_path="/",
                ),
                viewer_protocol_policy=aws_cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=aws_cloudfront.AllowedMethods.ALLOW_ALL,
                cached_methods=None,
                cache_policy=aws_cloudfront.CachePolicy(
                    self,
                    f"nucleoni-store-api-cloud-front-cache-policy",
                    cache_policy_name=f"nucleoni-store-api-cloud-front-cache-policy",
                    comment=f"nucleoni-store-api-cloud-front-cache-policy",
                    default_ttl=Duration.minutes(0),
                    min_ttl=Duration.minutes(0),
                    max_ttl=Duration.minutes(1),
                    cookie_behavior=aws_cloudfront.CacheCookieBehavior.all(),
                    header_behavior=aws_cloudfront.CacheHeaderBehavior.allow_list(
                        "x-atbion-app",
                        "Accept",
                        "Accept-Language",
                        "Accept-Encoding",
                        "Authorization",
                        "Content-Type",
                    ),
                ),
                origin_request_policy=aws_cloudfront.OriginRequestPolicy(
                    self,
                    f"nucleoni-store-api-cloud-front-cache-policy-front-origin-request-policy",
                    origin_request_policy_name=f"nucleoni-store-api-cloud-front-origin-request-policy",
                    comment=f"nucleoni-store-api-cloud-front-origin-request-policy",
                    cookie_behavior=aws_cloudfront.OriginRequestCookieBehavior.all(),
                    header_behavior=aws_cloudfront.OriginRequestHeaderBehavior.all(),
                    query_string_behavior=aws_cloudfront.OriginRequestQueryStringBehavior.all(),
                ),
                compress=True,
            ),
            domain_names=["store-api.nucleoni.com" if self.is_production else f"{self.stage}.store-api.nucleoni.com"],
            certificate=self.store_api_certificate,
        )

        aws_route53.ARecord(
            self,
            f"nucleoni-store-api-cloud-front-distribution-record",
            zone=self.hosted_zone,
            target=aws_route53.RecordTarget.from_alias(
                aws_route53_targets.CloudFrontTarget(
                    self.store_api_cloud_front_distribution
                )
            ),
            record_name="store-api.nucleoni.com" if self.is_production else f"{self.stage}.store-api.nucleoni.com",
        )
