#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os
import logging

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class OperationTypeNotFound(Exception):
    def __init__(self, message):
        super().__init__(message)


def system_handler():
    logger.info(
        f"SYSTEM HANDLER PROVISIONING_DATABASE_OPERATION: {os.environ.get('PROVISIONING_DATABASE_OPERATION')}")
    logger.info(f"SYSTEM HANDLER CUSTOMER_ID: {os.environ.get('CUSTOMER_ID')}")
    logger.info(
        f"SYSTEM HANDLER SETUP_DATABASE_STEP_TASK_TOKEN: {os.environ.get('SETUP_DATABASE_STEP_TASK_TOKEN')}")
    os.environ["DJANGO_SETTINGS_MODULE"] = "saleor.settings"
    import django
    from django.core import management
    from django.db import connections
    from saleor import settings
    import dj_database_url
    import boto3
    from dynamodb import dynamodb_json_dumps, dynamodb_json_loads

    django.setup()

    client_dynamodb = boto3.client("dynamodb")
    response = client_dynamodb.get_item(
        TableName=os.environ["NUCLEONI_PROVISIONING_TABLE_NAME"],
        Key=dynamodb_json_dumps({"customer_id": os.environ.get('CUSTOMER_ID')}),
    )

    customer_dict = dynamodb_json_loads(response["Item"])

    if os.environ.get("PROVISIONING_DATABASE_OPERATION") == "MIGRATE_DATABASE":
        logger.info("Migrating database...")
        client_databases = {
            settings.DATABASE_CONNECTION_DEFAULT_NAME: dj_database_url.config(
                default=f"postgres://{customer_dict['database_user']}:{customer_dict['database_password']}@{customer_dict['database_host']}:5432/{customer_dict['database_name']}",
                conn_max_age=settings.DB_CONN_MAX_AGE,
            ),
            settings.DATABASE_CONNECTION_REPLICA_NAME: dj_database_url.config(
                default=f"postgres://{customer_dict['database_user']}:{customer_dict['database_password']}@{customer_dict['database_host']}:5432/{customer_dict['database_name']}",
                conn_max_age=settings.DB_CONN_MAX_AGE,
            ),
        }
        settings.DATABASES[settings.DATABASE_CONNECTION_DEFAULT_NAME] = \
            client_databases[
                settings.DATABASE_CONNECTION_DEFAULT_NAME
            ]
        settings.DATABASES[settings.DATABASE_CONNECTION_REPLICA_NAME] = \
            client_databases[
                settings.DATABASE_CONNECTION_REPLICA_NAME
            ]
        connections.databases[settings.DATABASE_CONNECTION_DEFAULT_NAME] = \
            client_databases[
                settings.DATABASE_CONNECTION_DEFAULT_NAME
            ]
        connections.databases[settings.DATABASE_CONNECTION_REPLICA_NAME] = \
            client_databases[
                settings.DATABASE_CONNECTION_REPLICA_NAME
            ]
        management.call_command("migrate", "--noinput")
        logger.info("Database migrated")

        step_function_client = boto3.client("stepfunctions")
        step_function_client.send_task_success(
            taskToken=os.environ.get("SETUP_DATABASE_STEP_TASK_TOKEN"),
            output="Database migrated.",
        )

    return {
        "statusCode": 200,
    }


if __name__ == "__main__":
    system_handler()
