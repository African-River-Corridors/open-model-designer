"""Print the test files of one shard: `python tools/shard.py <shards> <index>`.

Files are dealt out largest first to the lightest shard (file size stands in for run time), so the shards are close in
size and no file sits in two of them. Every file in `tests/` except `tests/templates` (its own CI jobs) lands in exactly one shard.
"""

import pathlib
import sys


def shard(files: list[pathlib.Path], count: int, index: int) -> list[str]:
    loads = [0] * count
    mine: list[str] = []
    for f in sorted(files, key=lambda p: (-p.stat().st_size, str(p))):
        i = loads.index(min(loads))
        loads[i] += f.stat().st_size
        if i == index:
            mine.append(str(f))
    return sorted(mine)


if __name__ == "__main__":
    count, index = int(sys.argv[1]), int(sys.argv[2])
    files = sorted(
        p for p in pathlib.Path("tests").rglob("test_*.py") if "templates" not in p.parts
    )
    print(" ".join(shard(files, count, index)))
