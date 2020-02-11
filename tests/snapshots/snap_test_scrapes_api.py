# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()


snapshots[
    "test_cli_app_scrape_create[rent-92130-29-31] 1"
] = """🛠️The scrape has been kicked off.🛠️
(message id: ***volatile-value***)
"""
