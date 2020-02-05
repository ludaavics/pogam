# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots["TestHandlers.test_password_validation[hi] 1"] = {
    "body": {
        "data": None,
        "message": """Parameter validation failed:
Invalid length for parameter Password, value: 2, valid range: 6-inf""",
    },
    "statusCode": 400,
}

snapshots["TestHandlers.test_password_validation[H3l!o W] 1"] = {
    "body": {
        "data": None,
        "message": "The password must be at least 8 characters long, have both upper and lower case letters, and at least one special character.",
    },
    "statusCode": 400,
}

snapshots["TestHandlers.test_password_validation[h3llo world!] 1"] = {
    "body": {
        "data": None,
        "message": "The password must be at least 8 characters long, have both upper and lower case letters, and at least one special character.",
    },
    "statusCode": 400,
}

snapshots["TestHandlers.test_password_validation[H3LLO WORLD!] 1"] = {
    "body": {
        "data": None,
        "message": "The password must be at least 8 characters long, have both upper and lower case letters, and at least one special character.",
    },
    "statusCode": 400,
}

snapshots["TestHandlers.test_password_validation[H3llo World] 1"] = {
    "body": {
        "data": None,
        "message": "The password must be at least 8 characters long, have both upper and lower case letters, and at least one special character.",
    },
    "statusCode": 400,
}

snapshots["TestHandlers.test_invalid_invitation_code 1"] = {
    "body": {
        "data": None,
        "message": "Invalid invitation code. Please contact an administrator.",
    },
    "statusCode": 400,
}

snapshots["TestHandlers.test_signup 1"] = {
    "body": {
        "data": None,
        "message": "Your account has been created. Please check your email for the confirmation code.",
    },
    "statusCode": 200,
}
