# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""

from datetime import datetime

from saas.provisioning.models.rwmodels import RwModel


class CustomerProvisioningBase(RwModel):
    # customer
    is_aws_marketplace_integration: bool = None
    aws_marketplace_customer_id: str = None
    status: str = None
    customer_id: str = None
    # database
    is_database_created: bool = None
    is_database_provisioned: bool = None
    setup_database_step_task_token: str = None
    database_name: str = None
    database_host: str = None
    database_user: str = None
    database_password: str = None
    # storefront
    is_storefront_created: bool = None
    # dashboard
    is_dashboard_created: bool = None
    # datetime
    created_at: datetime = None
    updated_at: datetime = None
    # distribution
    distribution_id: str = None
    distribution_domain: str = None
    distribution_status: str = None
    distribution_arn: str = None
    distribution_custom_domain: str = None


class CustomerProvisioningIn(CustomerProvisioningBase):
    pass


class CustomerProvisioningDb(CustomerProvisioningBase):
    pass


class CustomerProvisioningOut(CustomerProvisioningBase):
    pass
