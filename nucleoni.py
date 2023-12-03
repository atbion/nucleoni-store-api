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

    django.setup()

    return {
        "statusCode": 200,
    }


if __name__ == "__main__":
    system_handler()
