# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""
import base64
import os
import re

import boto3
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from pymemcache.client.hash import HashClient


class SecurityService:
    @staticmethod
    def is_strong_password(password: str) -> bool:
        if len(password) < 8:
            return False
        if not re.search("[a-z]", password) or not re.search("[A-Z]", password):
            return False
        if not re.search("[0-9]", password):
            return False
        return True

    @staticmethod
    def get_secret(secret_arn: str):
        if secret_arn:
            client = boto3.client(
                service_name="secretsmanager",
                region_name=os.environ["DEPLOYMENT_REGION"],
            )
            response = client.get_secret_value(SecretId=secret_arn)
            if "SecretString" in response:
                secret = response["SecretString"]
                return secret
            else:
                secret = base64.b64decode(response["SecretBinary"])
                return secret
        return None

    @staticmethod
    def add_secret(secret_name: str, secret_value: str, secret_description):
        client = boto3.client("secretsmanager")
        client.create_secret(
            Name=secret_name,
            Description=secret_description,
            SecretString=secret_value,
        )

    @staticmethod
    def decrypt_ssm_parameter(parameter_encrypted: str, region: str = "eu-west-1"):
        client = HashClient(
            [
                os.environ.get("MEMCACHED_ENDPOINT"),
            ]
        )
        result = client.get(parameter_encrypted)
        if not result:
            session = boto3.Session()
            ssm_client = session.client("ssm", region_name=region)
            response = ssm_client.get_parameter(
                Name=parameter_encrypted, WithDecryption=True
            )
            value = response["Parameter"]["Value"]
            client.set(parameter_encrypted, value)
            return value
        return result.decode("utf-8")

    @staticmethod
    def get_aws_tmp_credentials():
        session = boto3.Session()
        credentials = session.get_credentials()
        credentials = credentials.get_frozen_credentials()
        access_key = credentials.access_key
        secret_key = credentials.secret_key
        session_token = credentials.token
        return {
            "access_key": access_key,
            "secret_key": secret_key,
            "session_token": session_token,
        }


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return str(user.pk) + str(timestamp) + str(user.is_active)
