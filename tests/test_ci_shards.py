"""The CI matrix runs every shard of the template audits: a shard count changed in the test but not in ci.yml fails here."""

import pathlib
import re

from templates import test_project_finance as t


def test_ci_names_every_template_audit_shard():
    ci = pathlib.Path(".github/workflows/ci.yml").read_text()
    listed = set(re.findall(r"^\s+- ((?:corruption|drive|inputs)-\d+of\d+)$", ci, re.M))
    want = {
        f"{kind}-{i}of{n}"
        for kind, n in (
            ("corruption", t.CORRUPTION_SHARDS),
            ("drive", t.DRIVE_SHARDS),
            ("inputs", t.INPUT_SHARDS),
        )
        for i in range(n)
    }
    assert listed == want
