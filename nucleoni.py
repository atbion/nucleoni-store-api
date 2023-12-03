#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import os
import logging

from saas.provisioning.crud.provisioning import ProvisioningCrud
from saas.provisioning.models.provisioning import CustomerProvisioningDb

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class OperationTypeNotFound(Exception):
    def __init__(self, message):
        super().__init__(message)


def system_handler():
    customer_id = os.environ.get("CUSTOMER_ID")
    logger.info(
        f"SYSTEM HANDLER PROVISIONING_DATABASE_OPERATION: {os.environ.get('PROVISIONING_DATABASE_OPERATION')}")
    logger.info(f"SYSTEM HANDLER CUSTOMER_ID: {customer_id}")
    logger.info(
        f"SYSTEM HANDLER SETUP_DATABASE_STEP_TASK_TOKEN: {os.environ.get('SETUP_DATABASE_STEP_TASK_TOKEN')}")
    os.environ["DJANGO_SETTINGS_MODULE"] = "saleor.settings"
    import django
    from django.core import management
    from django.db import connections
    from saleor import settings
    import dj_database_url
    import boto3

    django.setup()

    connections.close_all()

    customer_provisioning_db: CustomerProvisioningDb = ProvisioningCrud.get_customer_provisioning_impl(
        customer_id=customer_id,
    )

    if os.environ.get("PROVISIONING_DATABASE_OPERATION") == "MIGRATE_DATABASE":
        logger.info(f"Migrating database...{customer_provisioning_db.database_name}")
        client_databases = {
            settings.DATABASE_CONNECTION_DEFAULT_NAME: dj_database_url.config(
                default=f"postgres://{customer_provisioning_db.database_user}:{customer_provisioning_db.database_password}@{customer_provisioning_db.database_host}:5432/{customer_provisioning_db.database_name}",
                conn_max_age=settings.DB_CONN_MAX_AGE,
            ),
            settings.DATABASE_CONNECTION_REPLICA_NAME: dj_database_url.config(
                default=f"postgres://{customer_provisioning_db.database_user}:{customer_provisioning_db.database_password}@{customer_provisioning_db.database_host}:5432/{customer_provisioning_db.database_name}",
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

        management.call_command("migrate", noinput=True)
        logger.info(f"Database migrated: {customer_provisioning_db.database_name}")

        customer_provisioning_db.is_database_provisioned = True
        ProvisioningCrud.update_customer_provisioning_impl(
            customer_provisioning_db=customer_provisioning_db,
        )

        step_function_client = boto3.client("stepfunctions")
        step_function_client.send_task_success(
            taskToken=os.environ.get("SETUP_DATABASE_STEP_TASK_TOKEN"),
            output=f"Database migrated: {customer_provisioning_db.database_name}",
        )

    return {
        "statusCode": 200,
    }


if __name__ == "__main__":
    system_handler()
