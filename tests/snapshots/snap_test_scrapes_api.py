# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots[
    "test_cli_app_scrape_create[rent-92130-29-31-True] 1"
] = """🛠️The scrape has been kicked off.🛠️
(message id: ***volatile-value***)
"""

snapshots[
    "test_cli_app_scrape_create[rent-92130-29-31-False] 1"
] = """Account 'test' is not logged in. Please log in and try again.
"""
