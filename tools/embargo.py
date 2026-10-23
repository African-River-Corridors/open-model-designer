"""The one embargo list, used by the release guard.

The repo may become public, so the list must not publish the names it protects. It holds the SHA-256 of
each lowercased term instead. A term is one to three words; a multi-word term is its words joined
by one space ("north channel").

Matching: each line is lowercased and split into words (runs of a-z and 0-9; everything else,
including `_`, `-`, `.` and `/`, separates words). Every run of 1-3 consecutive words is hashed
and looked up. So matching is whole-word: an embargoed word inside a longer word is not a hit.

A hit is reported by its term id: the first 12 hex digits of the term's hash. Path rules (machine-
local paths) are not secret and are plain patterns.

Maintain the list from the private plaintext copy, which never enters the repo:

    python tools/embargo.py --hash < terms.txt     # prints the new TERM_HASHES body
    python tools/embargo.py --id "some term"       # the id the guard prints for a term

Standard library only.
"""
from __future__ import annotations

import hashlib
import re
import sys

MAX_WORDS = 3
ID_LEN = 12

TERM_HASHES = frozenset({
    "54a50220223cd709ddf9a1ff6a0fbbcf730f6118b1b962d8694c8d973f94a554",
    "74dd17a579debfa10466572e52ac96bf8e704f93a158c8a1883eac6bb572bab9",
    "98d144fa7e3b819c40e8e88bf309949d1e405b3ce35a1b38fe1b435ea989b367",
    "c6c43dad9bb5474670afdf38c6ea916b173b68f014ef3435dbbbb92820fadf61",
    "d3cec99112255db9bf4963f7798562b6a36f1bd0b2016918629e007d474deb70",
    "fc4f9c94394e55c0c42baa313bb1d8717a4024c671ead9b4faae1eb81ff2edba",
})

# Path rules: not secret, so plain patterns. name -> pattern.
PATH_RULES = {
    "/" "Users/": re.compile(r"/[u]sers/", re.IGNORECASE),
}

_WORD = re.compile(r"[a-z0-9]+")


def term_hash(term: str) -> str:
    """SHA-256 of a term, normalised the way lines are: lowercase words joined by one space."""
    return hashlib.sha256(" ".join(_WORD.findall(term.lower())).encode()).hexdigest()


def term_id(term: str) -> str:
    return term_hash(term)[:ID_LEN]


def find(line: str, hashes: frozenset[str] | None = None) -> list[tuple[str, str]]:
    """Every embargo hit in one line, as (term id, matched text). Ordered, de-duplicated."""
    hashes = TERM_HASHES if hashes is None else hashes
    words = _WORD.findall(line.lower())
    out: list[tuple[str, str]] = []
    seen = set()
    for i in range(len(words)):
        for n in range(1, MAX_WORDS + 1):
            if i + n > len(words):
                break
            gram = " ".join(words[i:i + n])
            h = hashlib.sha256(gram.encode()).hexdigest()
            if h in hashes and h[:ID_LEN] not in seen:
                seen.add(h[:ID_LEN])
                out.append((h[:ID_LEN], gram))
    for name, pat in PATH_RULES.items():
        m = pat.search(line)
        if m and name not in seen:
            seen.add(name)
            out.append((name, m.group(0)))
    return out


def find_lines(lines, hashes: frozenset[str] | None = None) -> list[tuple[int, str, str]]:
    """Like `find`, but a term may wrap over line ends. `lines` is (line number, text) pairs.
    Words run on across lines whose numbers are consecutive; a gap in the numbers (a diff hunk
    boundary) breaks the run. A hit is reported at the line of its first word, as
    (line number, term id, matched words)."""
    hashes = TERM_HASHES if hashes is None else hashes
    out: list[tuple[int, str, str]] = []
    seen: set[tuple[int, str]] = set()

    def add(n: int, tid: str, gram: str) -> None:
        if (n, tid) not in seen:
            seen.add((n, tid))
            out.append((n, tid, gram))

    run: list[tuple[int, str]] = []             # (line number, word) since the last gap

    def flush() -> None:
        for i in range(len(run)):
            for k in range(1, MAX_WORDS + 1):
                if i + k > len(run):
                    break
                gram = " ".join(w for _, w in run[i:i + k])
                h = hashlib.sha256(gram.encode()).hexdigest()
                if h in hashes:
                    add(run[i][0], h[:ID_LEN], gram)
        run.clear()

    last = None
    for n, text in lines:
        if last is not None and n != last + 1:
            flush()
        last = n
        run.extend((n, w) for w in _WORD.findall(text.lower()))
        for name, pat in PATH_RULES.items():
            m = pat.search(text)
            if m:
                add(n, name, m.group(0))
    flush()
    return sorted(out, key=lambda t: t[0])


def contains(text: str, hashes: frozenset[str] | None = None) -> list[str]:
    """Sorted term ids found anywhere in a text (any line)."""
    return sorted({tid for line in text.splitlines() for tid, _ in find(line, hashes)})


def known_id(term: str) -> str | None:
    """Resolve an allowlist term: '*', a path-rule name, a term id (hex prefix), or the term
    itself. Returns the id, or None if it names nothing on the list."""
    t = term.strip()
    if t == "*":
        return "*"
    for name in PATH_RULES:
        if t.lower() == name.lower():
            return name
    if re.fullmatch(r"[0-9a-f]{%d,64}" % ID_LEN, t.lower()):
        pre = t.lower()
        if any(h.startswith(pre) for h in TERM_HASHES):
            return pre[:ID_LEN]
    h = term_hash(t)
    return h[:ID_LEN] if h in TERM_HASHES else None


def _main(argv: list[str]) -> int:
    if argv[:1] == ["--hash"]:
        terms = [ln.strip() for ln in sys.stdin if ln.strip() and not ln.lstrip().startswith("#")]
        for h in sorted({term_hash(t) for t in terms}):
            print(f'    "{h}",')
        return 0
    if argv[:1] == ["--id"] and len(argv) == 2:
        print(term_id(argv[1]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
