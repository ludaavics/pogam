# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots["TestHandlers.test_user_creation 1"] = {
    "body": {
        "data": None,
        "message": "Invalid invitation code. Please contact an administrator.",
    },
    "statusCode": 400,
}

snapshots["TestHandlers.test_user_creation 2"] = {
    "body": {
        "data": None,
        "message": "Your account has been created. Please check your email for the confirmation code.",
    },
    "statusCode": 200,
}

snapshots["TestHandlers.test_user_creation 3"] = {
    "body": {
        "data": None,
        "message": "Invalid invitation code. Please contact an administrator.",
    },
    "statusCode": 400,
}
