# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 1"
] = """[]
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 2"
] = """✨All done! 🍰 The search has been scheduled. ✨
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 3"
] = """✨All done! 🍰 The search has been scheduled. ✨
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 4"
] = """✨All done! 🍰 The search has been scheduled. ✨
"""

snapshots["test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 5"] = [
    {
        "name": "pogam-test-rent-92130-leboncoin-seloger-***volatile***",
        "notify": {},
        "schedule": "cron(0 3/6 * * ? *)",
        "search": {
            "max_beds": None,
            "max_duplicates": 25,
            "max_price": None,
            "max_rooms": None,
            "max_size": 31.0,
            "min_beds": None,
            "min_price": None,
            "min_rooms": None,
            "min_size": 27.0,
            "num_results": 100,
            "post_codes": ["92130"],
            "property_types": ["apartment", "house"],
            "sources": ["leboncoin", "seloger"],
            "transaction": "rent",
        },
    },
    {
        "name": "pogam-test-rent-92130-leboncoin-seloger-***volatile***",
        "notify": {},
        "schedule": "cron(0 3/6 * * ? *)",
        "search": {
            "max_beds": None,
            "max_duplicates": 25,
            "max_price": None,
            "max_rooms": None,
            "max_size": 31.0,
            "min_beds": None,
            "min_price": None,
            "min_rooms": None,
            "min_size": 28.0,
            "num_results": 100,
            "post_codes": ["92130"],
            "property_types": ["apartment", "house"],
            "sources": ["leboncoin", "seloger"],
            "transaction": "rent",
        },
    },
    {
        "name": "pogam-test-rent-92130-leboncoin-seloger-***volatile***",
        "notify": {},
        "schedule": "cron(0 3/6 * * ? *)",
        "search": {
            "max_beds": None,
            "max_duplicates": 25,
            "max_price": None,
            "max_rooms": None,
            "max_size": 31.0,
            "min_beds": None,
            "min_price": None,
            "min_rooms": None,
            "min_size": 29.0,
            "num_results": 100,
            "post_codes": ["92130"],
            "property_types": ["apartment", "house"],
            "sources": ["leboncoin", "seloger"],
            "transaction": "rent",
        },
    },
]

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 6"
] = """This search is already scheduled! To overwrite it re-submit the request with 'force' set to true.

"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 7"
] = """✨All done! 🍰 The search has been scheduled. ✨
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 8"
] = """Rule 'foo' not found.

"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 9"
] = """✨All done! 🍰 The search has been deleted. ✨

"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-True] 10"
] = """✨All done! 🍰 Deleted 2 tasks.✨
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-False] 1"
] = """Account 'test' is not logged in. Please log in and try again.
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-False] 2"
] = """Account 'test' is not logged in. Please log in and try again.
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-False] 3"
] = """Account 'test' is not logged in. Please log in and try again.
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-False] 4"
] = """Account 'test' is not logged in. Please log in and try again.
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-False] 5"
] = """Account 'test' is not logged in. Please log in and try again.
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-False] 6"
] = """Account 'test' is not logged in. Please log in and try again.
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-False] 7"
] = """Account 'test' is not logged in. Please log in and try again.
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-False] 8"
] = """Account 'test' is not logged in. Please log in and try again.
"""

snapshots[
    "test_cli_app_scrape_schedule_crud[rent-92130-29-31-False] 9"
] = """Account 'test' is not logged in. Please log in and try again.
"""
