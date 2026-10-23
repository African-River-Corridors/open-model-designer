"""Every `docs/golden-cases/...` path a golden source names is a file that exists."""

import re
from pathlib import Path

from omd.registry import discover

ROOT = Path(__file__).resolve().parent.parent
PATH = re.compile(r"docs/golden-cases/[\w.]+")
TOY = {"levy"}  # the toy module's golden case is a one-line sum, with no working file


def problems(sources: dict[str, str]) -> list[str]:
    """One line per source that names no working file, or names one that is not in the repo."""
    out = []
    for name, source in sources.items():
        paths = PATH.findall(source)
        if not paths:
            out.append(f"{name}: names no docs/golden-cases file")
        out += [f"{name}: {p} does not exist" for p in paths if not (ROOT / p).is_file()]
    return out


def test_every_golden_source_names_a_working_file_that_exists():
    sources = {n: m.golden.source for n, m in discover("omd.modules").items() if n not in TOY}
    assert len(sources) >= 25
    assert problems(sources) == []


def test_the_check_reads_red_for_a_missing_file_and_for_no_file():
    got = problems(
        {
            "a": "x; working in docs/golden-cases/no_such_case.answer.md",
            "b": "working kept elsewhere",
            "c": "working in docs/golden-cases/cfads.answer.md",
        }
    )
    assert got == [
        "a: docs/golden-cases/no_such_case.answer.md does not exist",
        "b: names no docs/golden-cases file",
    ]
