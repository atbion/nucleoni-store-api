# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import json
import logging
import os
import uuid
from enum import Enum
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

import boto3

from saas.provisioning.core.security import SecurityService
from saas.provisioning.crud.provisioning import ProvisioningCrud
from saas.provisioning.models.provisioning import CustomerProvisioningDb

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class ProvisioningStatus(Enum):
    NOT_READY_TO_PROVISIONING = "NOT_READY_TO_PROVISIONING"
    READY_TO_PROVISIONING = "READY_TO_PROVISIONING"
    PROVISIONING_START_PROVISIONING_STEP_INIT = "PROVISIONING_START_PROVISIONING_STEP_INIT"
    PROVISIONING_START_PROVISIONING_STEP_END = "PROVISIONING_START_PROVISIONING_STEP_END"
    PROVISIONING_SETUP_DATABASE_STEP_INIT = "PROVISIONING_SETUP_DATABASE_STEP_INIT"
    PROVISIONING_SETUP_DATABASE_STEP_END = "PROVISIONING_SETUP_DATABASE_STEP_END"
    PROVISIONING_SETUP_DISTRIBUTION_STEP_INIT = "PROVISIONING_SETUP_DISTRIBUTION_STEP_INIT"
    PROVISIONING_SETUP_DISTRIBUTION_STEP_END = "PROVISIONING_SETUP_DISTRIBUTION_STEP_END"
    PROVISIONING_END_PROVISIONING_STEP_INIT = "PROVISIONING_END_PROVISIONING_STEP_INIT"
    PROVISIONING_END_PROVISIONING_STEP_END = "PROVISIONING_END_PROVISIONING_STEP_END"
    PROVISIONED = "PROVISIONED"
    WITH_ERRORS = "WITH_ERRORS"


class ProvisioningDatabaseOperations(Enum):
    CREATE_DATABASE = "CREATE_DATABASE"
    MIGRATE_DATABASE = "MIGRATE_DATABASE"


class ProvisioningService:
    @staticmethod
    def process_provisioning_requests(body: dict):
        customer_provisioning: CustomerProvisioningDb = CustomerProvisioningDb(**body)
        stepfunctions_client = boto3.client("stepfunctions")
        stepfunctions_client.start_execution(
            stateMachineArn=os.environ["NUCLEONI_PROVISIONING_STEP_FUNCTION_ARN"],
            input=json.dumps(customer_provisioning.model_dump(), default=str),
        )

    @staticmethod
    def process_provisioning_workflow(event, context):
        logger.info(f"STATE_NAME: {event['state_name']}")
        if (
                event["state_name"]
                == "StartProvisioningStep"
        ):
            return ProvisioningService.process_provisioning_workflow_start_provisioning_step(
                event=event, context=context
            )
        if (
                event["state_name"]
                == "SetupDatabaseStep"
        ):
            return ProvisioningService.process_provisioning_workflow_setup_database_step(
                event=event, context=context
            )
        if (
                event["state_name"]
                == "SetupDistributionStep"
        ):
            return ProvisioningService.process_provisioning_workflow_setup_distribution_step(
                event=event, context=context
            )
        if (
                event["state_name"]
                == "EndProvisioningStep"
        ):
            return ProvisioningService.process_provisioning_workflow_end_provisioning_step(
                event=event, context=context
            )
        return event

    @staticmethod
    def process_provisioning_workflow_start_provisioning_step(event, context):
        logger.info(f"STATE_NAME: {event['state_name']}")
        logger.info(f"PAYLOAD: {event['payload']}")
        customer_provisioning_db = ProvisioningCrud.get_customer_provisioning_impl(
            customer_id=event["payload"]["customer_id"]
        )
        customer_provisioning_db.status = ProvisioningStatus.PROVISIONING_START_PROVISIONING_STEP_INIT.value
        customer_provisioning_db = ProvisioningCrud.update_customer_provisioning_impl(
            customer_provisioning_db=customer_provisioning_db
        )

        logger.info(f"customer_provisioning_db: {customer_provisioning_db.model_dump()}")

        # Other initialization steps maybe here ?

        customer_provisioning_db = ProvisioningCrud.get_customer_provisioning_impl(
            customer_id=event["payload"]["customer_id"]
        )
        customer_provisioning_db.status = ProvisioningStatus.PROVISIONING_START_PROVISIONING_STEP_END.value
        customer_provisioning_db = ProvisioningCrud.update_customer_provisioning_impl(
            customer_provisioning_db=customer_provisioning_db
        )

        logger.info(f"customer_provisioning_db: {customer_provisioning_db.model_dump()}")
        return json.loads(json.dumps(customer_provisioning_db.model_dump(), default=str))

    @staticmethod
    def process_provisioning_workflow_setup_database_step(event, context):
        logger.info(f"STATE_NAME: {event['state_name']}")
        logger.info(f"PAYLOAD: {event['payload']}")

        customer_provisioning_db = ProvisioningCrud.get_customer_provisioning_impl(
            customer_id=event["payload"]["Payload"]["customer_id"]
        )
        customer_provisioning_db.setup_database_step_task_token = event["task_token"]
        customer_provisioning_db.status = ProvisioningStatus.PROVISIONING_SETUP_DATABASE_STEP_INIT.value
        customer_provisioning_db = ProvisioningCrud.update_customer_provisioning_impl(
            customer_provisioning_db=customer_provisioning_db
        )

        if not customer_provisioning_db.is_database_created:
            root_user = "nucleoni"
            root_password = SecurityService.decrypt_ssm_parameter(
                parameter_encrypted=os.environ.get("AURORA_PASSWORD_SSM_PARAMETER")
            )
            database_name = uuid.uuid4().hex
            database_host = os.environ.get("AURORA_ENDPOINT")
            database_user = uuid.uuid4().hex
            database_password = SecurityService.generate_strong_password()

            # Connect to database
            con = psycopg2.connect(
                user=root_user,
                password=root_password,
                host=database_host,
                dbname='postgres',
            )
            con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = con.cursor()
            # create user
            query = sql.SQL("CREATE USER {username} WITH PASSWORD {password}").format(
                username=sql.Identifier(database_user),
                password=sql.Placeholder()
            )
            cur.execute(query, (database_password,))
            # create database
            cur.execute(sql.SQL("CREATE DATABASE {database_name}").format(
                database_name=sql.Identifier(database_name),
            ),
            )
            # grant privileges
            cur.execute(sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {database_name} TO {username}").format(
                database_name=sql.Identifier(database_name),
                username=sql.Identifier(database_user),
            ),
            )

            customer_provisioning_db.database_name = database_name
            customer_provisioning_db.database_host = database_host
            customer_provisioning_db.database_user = database_user
            customer_provisioning_db.database_password = database_password
            customer_provisioning_db.is_database_created = True
            customer_provisioning_db = ProvisioningCrud.update_customer_provisioning_impl(
                customer_provisioning_db=customer_provisioning_db
            )
        # Launch fargate task to update database
        ecs_client = boto3.client("ecs")
        response = ecs_client.run_task(
            cluster=os.environ.get("NUCLEONI_COMMON_ECS_CLUSTER_ARN"),
            taskDefinition=os.environ.get("NUCLEONI_STORE_API_TASK_DEFINITION_ARN"),
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": [
                        # TODO it needs to be public subnet
                        os.environ.get("VPC_ATBION_PUBLIC_SUBNET_1"),
                    ],
                    "securityGroups": [
                        os.environ.get("STORE_API_PROVISIONING_TASK_DEFINITION_SG_ID"),
                    ],
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": f"store-api-container-{os.environ.get('STAGE')}",
                        'command': [
                            '/usr/local/bin/python3.9',
                            '/app/nucleoni.py',
                        ],
                        "environment": [
                            {
                                "name": "CUSTOMER_ID",
                                "value": customer_provisioning_db.customer_id,
                            },
                            {
                                "name": "PROVISIONING_DATABASE_OPERATION",
                                "value": ProvisioningDatabaseOperations.MIGRATE_DATABASE.value,
                            },
                            {
                                "name": "SETUP_DATABASE_STEP_TASK_TOKEN",
                                "value": customer_provisioning_db.setup_database_step_task_token,
                            },
                        ],
                    }
                ]
            },
        )
        logger.info(f"response: {response}")
        logger.info(f"customer_provisioning_db: {customer_provisioning_db.model_dump()}")
        return json.loads(json.dumps(customer_provisioning_db.model_dump(), default=str))

    @staticmethod
    def process_provisioning_workflow_setup_distribution_step(event, context):
        logger.info(f"STATE_NAME: {event['state_name']}")
        logger.info(f"PAYLOAD: {event['payload']}")
        return event

    @staticmethod
    def process_provisioning_workflow_end_provisioning_step(event, context):
        logger.info(f"STATE_NAME: {event['state_name']}")
        logger.info(f"PAYLOAD: {event['payload']}")
        return event
