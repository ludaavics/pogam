# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots["TestHandlers.test_crud 1"] = {
    "body": {"data": [], "message": ""},
    "statusCode": 200,
}

snapshots["TestHandlers.test_crud 2"] = {
    "body": {
        "data": [
            {
                "name": "pogam-test-rent-92130-leboncoin-seloger",
                "schedule": "cron(0 3/6 * * ? *)",
                "search": {
                    "max_beds": None,
                    "max_duplicates": 25,
                    "max_price": None,
                    "max_rooms": None,
                    "max_size": None,
                    "min_beds": None,
                    "min_price": None,
                    "min_rooms": None,
                    "min_size": None,
                    "num_results": 100,
                    "post_codes": ["92130"],
                    "property_types": ["apartment", "house"],
                    "sources": ["leboncoin", "seloger"],
                    "transaction": "rent",
                },
            }
        ],
        "message": "",
    },
    "statusCode": 201,
}

snapshots["TestHandlers.test_crud 3"] = {
    "body": {
        "data": [
            {
                "name": "pogam-test-buy-92130-leboncoin-seloger",
                "schedule": "cron(0 3/6 * * ? *)",
                "search": {
                    "max_beds": None,
                    "max_duplicates": 25,
                    "max_price": None,
                    "max_rooms": None,
                    "max_size": None,
                    "min_beds": None,
                    "min_price": None,
                    "min_rooms": None,
                    "min_size": None,
                    "num_results": 100,
                    "post_codes": ["92130"],
                    "property_types": ["apartment", "house"],
                    "sources": ["leboncoin", "seloger"],
                    "transaction": "buy",
                },
            }
        ],
        "message": "",
    },
    "statusCode": 201,
}

snapshots["TestHandlers.test_crud 4"] = {
    "body": {
        "data": [
            {
                "name": "pogam-test-buy-92130-leboncoin-seloger",
                "notify": {},
                "schedule": "cron(0 3/6 * * ? *)",
                "search": {
                    "max_beds": None,
                    "max_duplicates": 25,
                    "max_price": None,
                    "max_rooms": None,
                    "max_size": None,
                    "min_beds": None,
                    "min_price": None,
                    "min_rooms": None,
                    "min_size": None,
                    "num_results": 100,
                    "post_codes": ["92130"],
                    "property_types": ["apartment", "house"],
                    "sources": ["leboncoin", "seloger"],
                    "transaction": "buy",
                },
            },
            {
                "name": "pogam-test-rent-92130-leboncoin-seloger",
                "notify": {},
                "schedule": "cron(0 3/6 * * ? *)",
                "search": {
                    "max_beds": None,
                    "max_duplicates": 25,
                    "max_price": None,
                    "max_rooms": None,
                    "max_size": None,
                    "min_beds": None,
                    "min_price": None,
                    "min_rooms": None,
                    "min_size": None,
                    "num_results": 100,
                    "post_codes": ["92130"],
                    "property_types": ["apartment", "house"],
                    "sources": ["leboncoin", "seloger"],
                    "transaction": "rent",
                },
            },
        ],
        "message": "",
    },
    "statusCode": 200,
}

snapshots["TestHandlers.test_crud 5"] = {
    "body": {
        "data": "",
        "message": "This search is already scheduled! To overwrite it re-submit the "
        "request with 'force' set to true.",
    },
    "statusCode": 409,
}

snapshots["TestHandlers.test_crud 6"] = {
    "body": {
        "data": [
            {
                "name": "pogam-test-rent-92130-leboncoin-seloger",
                "schedule": "cron(0 3/6 * * ? *)",
                "search": {
                    "max_beds": None,
                    "max_duplicates": 25,
                    "max_price": 1500,
                    "max_rooms": None,
                    "max_size": None,
                    "min_beds": None,
                    "min_price": None,
                    "min_rooms": None,
                    "min_size": None,
                    "num_results": 100,
                    "post_codes": ["92130"],
                    "property_types": ["apartment", "house"],
                    "sources": ["leboncoin", "seloger"],
                    "transaction": "rent",
                },
            }
        ],
        "message": "",
    },
    "statusCode": 201,
}

snapshots["TestHandlers.test_crud 7"] = {
    "body": {"data": {}, "message": ""},
    "statusCode": 204,
}

snapshots["TestHandlers.test_crud 8"] = {
    "body": {"data": {}, "message": ""},
    "statusCode": 204,
}
