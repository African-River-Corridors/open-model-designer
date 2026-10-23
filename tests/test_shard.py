"""tools/shard.py: every test file lands in exactly one shard."""

import pathlib

import shard


def test_every_test_file_is_in_exactly_one_shard():
    files = sorted(
        p for p in pathlib.Path("tests").rglob("test_*.py") if "templates" not in p.parts
    )
    dealt = [f for i in range(4) for f in shard.shard(files, 4, i)]
    assert sorted(dealt) == sorted(str(f) for f in files)
