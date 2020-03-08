# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots["test_known_query[success-overrides0] 1"] = {
    "filters": {
        "category": {"id": "10"},
        "enums": {"ad_type": ["offer"], "real_estate_type": ["2", "1"]},
        "location": {"locations": [{"locationType": "city", "zipcode": "92130"}]},
        "ranges": {"price": {}, "rooms": {}, "square": {}},
    },
    "limit": 100,
    "limit_alu": 1,
    "pivot": "0,0,0",
    "sort_by": "time",
    "sort_order": "desc",
}

snapshots["test_known_query[success-overrides0] 2"] = {
    "filters": {
        "category": {"id": "10"},
        "enums": {"ad_type": ["offer"], "real_estate_type": ["2", "1"]},
        "location": {"locations": [{"locationType": "city", "zipcode": "92130"}]},
        "ranges": {"price": {}, "rooms": {}, "square": {}},
    },
    "limit": 100,
    "limit_alu": 1,
    "pivot": "1578659785000|1733474533",
    "sort_by": "time",
    "sort_order": "desc",
}

snapshots["test_known_query[success-overrides0] 3"] = {
    "filters": {
        "category": {"id": "10"},
        "enums": {"ad_type": ["offer"], "real_estate_type": ["2", "1"]},
        "location": {"locations": [{"locationType": "city", "zipcode": "92130"}]},
        "ranges": {"price": {}, "rooms": {}, "square": {}},
    },
    "limit": 100,
    "limit_alu": 1,
    "pivot": "1578659785000|1733474533",
    "sort_by": "time",
    "sort_order": "desc",
}

snapshots["test_known_query[success-overrides1] 1"] = {
    "filters": {
        "category": {"id": "10"},
        "enums": {"ad_type": ["offer"], "real_estate_type": ["2", "1"]},
        "location": {"locations": [{"locationType": "city", "zipcode": "92130"}]},
        "ranges": {
            "price": {"max": 1500, "min": 500},
            "rooms": {"max": 3, "min": 1},
            "square": {"max": 50, "min": 30},
        },
    },
    "limit": 100,
    "limit_alu": 1,
    "pivot": "0,0,0",
    "sort_by": "time",
    "sort_order": "desc",
}

snapshots["test_known_query[success-overrides2] 1"] = {
    "filters": {
        "category": {"id": "10"},
        "enums": {"ad_type": ["offer"], "real_estate_type": ["2", "1"]},
        "location": {
            "locations": [{"department_id": 92, "locationType": "department"}]
        },
        "ranges": {"price": {}, "rooms": {}, "square": {}},
    },
    "limit": 100,
    "limit_alu": 1,
    "pivot": "0,0,0",
    "sort_by": "time",
    "sort_order": "desc",
}

snapshots["test_known_query[success-overrides3] 1"] = {
    "filters": {
        "category": {"id": "10"},
        "enums": {"ad_type": ["offer"], "real_estate_type": ["2", "1"]},
        "location": {
            "locations": [
                {"locationType": "city", "zipcode": 75016},
                {"department_id": 92, "locationType": "department"},
            ]
        },
        "ranges": {"price": {}, "rooms": {}, "square": {}},
    },
    "limit": 100,
    "limit_alu": 1,
    "pivot": "0,0,0",
    "sort_by": "time",
    "sort_order": "desc",
}
