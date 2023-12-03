# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""

import os

import boto3
import botocore

from saas.provisioning.core.dynamodb import (
    dynamodb_json_dumps,
    check_dynamodb_response,
    dynamodb_json_loads,
)
from saas.provisioning.models.provisioning import (
    CustomerProvisioningIn,
    CustomerProvisioningDb,
)


class CustomerProvisioningAlreadyExists(Exception):
    def __init__(self, message):
        super().__init__(message)


class CustomerProvisioningDoNotExists(Exception):
    def __init__(self, message):
        super().__init__(message)


class ProvisioningCrud:
    @staticmethod
    def add_customer_provisioning_impl(
        customer_provisioning_in: CustomerProvisioningIn,
    ):
        try:
            client_dynamodb = boto3.client("dynamodb")
            transact_items = [
                {
                    "Put": {
                        "TableName": os.environ[
                            "NUCLEONI_PROVISIONING_TABLE_NAME"
                        ],
                        "Item": dynamodb_json_dumps(customer_provisioning_in.model_dump()),
                        "ConditionExpression": "attribute_not_exists(customer_id)",
                    },
                }
            ]
            response = client_dynamodb.transact_write_items(
                TransactItems=transact_items
            )
            check_dynamodb_response(response)
            return ProvisioningCrud.get_customer_provisioning_impl(
                customer_id=customer_provisioning_in.customer_id,
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise CustomerProvisioningAlreadyExists(
                    message=f"Customer provisioning already exists, customer_id: {customer_provisioning_in.customer_id}."
                )

    @staticmethod
    def get_customer_provisioning_impl(
        customer_id: str,
    ):
        client_dynamodb = boto3.client("dynamodb")
        response = client_dynamodb.get_item(
            TableName=os.environ["NUCLEONI_PROVISIONING_TABLE_NAME"],
            Key=dynamodb_json_dumps({"customer_id": customer_id}),
        )
        check_dynamodb_response(response)
        if "Item" not in response:
            return None
        customer_provisioning_db: CustomerProvisioningDb = CustomerProvisioningDb(
            **dynamodb_json_loads(response["Item"])
        )
        return customer_provisioning_db

    @staticmethod
    def update_customer_provisioning_impl(
        customer_provisioning_db: CustomerProvisioningDb,
    ):
        try:
            client_dynamodb = boto3.client("dynamodb")
            transact_items = [
                {
                    "Put": {
                        "TableName": os.environ[
                            "NUCLEONI_PROVISIONING_TABLE_NAME"
                        ],
                        "Item": dynamodb_json_dumps(customer_provisioning_db.model_dump()),
                        "ConditionExpression": "attribute_exists(customer_id)",
                    },
                }
            ]
            response = client_dynamodb.transact_write_items(
                TransactItems=transact_items
            )
            check_dynamodb_response(response)
            return ProvisioningCrud.get_customer_provisioning_impl(
                customer_id=customer_provisioning_db.customer_id
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise CustomerProvisioningAlreadyExists(
                    message=f"Customer provisioning do not exists, customer_id: {customer_provisioning_db.customer_id}."
                )

    @staticmethod
    def delete_customer_provisioning_impl(
        customer_provisioning_db: CustomerProvisioningDb,
    ):
        try:
            client_dynamodb = boto3.client("dynamodb")

            transact_items = [
                {
                    "Delete": {
                        "TableName": os.environ[
                            "NUCLEONI_PROVISIONING_TABLE_NAME"
                        ],
                        "Key": {
                            "customer_id": {"S": customer_provisioning_db.customer_id},
                        },
                    },
                }
            ]
            response = client_dynamodb.transact_write_items(
                TransactItems=transact_items
            )
            check_dynamodb_response(response)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise CustomerProvisioningDoNotExists(
                    message=f"Customer provisioning do not exists, customer_id: {customer_provisioning_db.customer_id}."
                )
