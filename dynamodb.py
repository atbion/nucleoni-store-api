# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""

import re
import uuid
from decimal import Decimal
import six
from datetime import datetime
import simplejson as json
from boto3.dynamodb.types import TypeSerializer


class DynamoDbError(Exception):
    def __init__(self, message):
        super().__init__(message)


def json_serial(o):
    if isinstance(o, datetime):
        serial = o.strftime("%Y-%m-%dT%H:%M:%S.%f")
    elif isinstance(o, Decimal):
        if o % 1 > 0:
            serial = float(o)
        else:
            serial = int(o)
    elif isinstance(o, uuid.UUID):
        serial = str(o.hex)
    elif isinstance(o, set):
        serial = list(o)
    else:
        serial = o
    return serial


def dynamodb_json_dumps(dct, **kwargs):
    """Dump the dict to json in DynamoDB Format
    You can use any other simplejson or json options
    :param dct - the dict to dump
    :returns: DynamoDB json format.
    """

    result_ = TypeSerializer().serialize(
        json.loads(json.dumps(dct, default=json_serial), use_decimal=True)
    )
    return next(six.iteritems(result_))[1]


def object_hook(dct):
    """DynamoDB object hook to return python values"""
    try:
        # First - Try to parse the dct as DynamoDB parsed
        if "BOOL" in dct:
            return dct["BOOL"]
        if "S" in dct:
            val = dct["S"]
            try:
                return datetime.strptime(val, "%Y-%m-%dT%H:%M:%S.%f")
            except:
                return str(val)
        if "SS" in dct:
            return list(dct["SS"])
        if "N" in dct:
            if re.match("^-?\d+?\.\d+?$", dct["N"]) is not None:
                return float(dct["N"])
            else:
                try:
                    return int(dct["N"])
                except:
                    return int(dct["N"])
        if "B" in dct:
            return str(dct["B"])
        if "NS" in dct:
            return set(dct["NS"])
        if "BS" in dct:
            return set(dct["BS"])
        if "M" in dct:
            return dct["M"]
        if "L" in dct:
            return dct["L"]
        if "NULL" in dct and dct["NULL"] is True:
            return None
    except:
        return dct

    # In a Case of returning a regular python dict
    for key, val in six.iteritems(dct):
        if isinstance(val, six.string_types):
            try:
                dct[key] = datetime.strptime(val, "%Y-%m-%dT%H:%M:%S.%f")
            except:
                # This is a regular Basestring object
                pass

        if isinstance(val, Decimal):
            if val % 1 > 0:
                dct[key] = float(val)
            else:
                dct[key] = int(val)

    return dct


def dynamodb_json_loads(s, *args, **kwargs):
    """Loads dynamodb json format to a python dict.
    :param s - the json string or dict (with the as_dict variable set to True) to convert
    :returns python dict object
    """
    if not isinstance(s, six.string_types):
        s = json.dumps(s)
    kwargs["object_hook"] = object_hook
    return json.loads(s, *args, **kwargs)


def check_dynamodb_response(response):
    if (
        "ResponseMetadata" not in response
        or "HTTPStatusCode" not in response["ResponseMetadata"]
        or response["ResponseMetadata"]["HTTPStatusCode"] != 200
    ):
        raise DynamoDbError(message=json.dumps(response, default=str))
