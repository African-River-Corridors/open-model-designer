"""The leak guard must go red on a guarded term, and stay green on clean text."""

import subprocess
from pathlib import Path

import embargo
import release_guard

FAKE = "zorblax"
FAKE_HASHES = frozenset({embargo.term_hash(FAKE)})
# Real guarded terms, built in pieces so this file does not hold them whole.
REAL = ["Anko" + "bra", "CC" + "GT", "Gha" + "na", "Gen" + "ser", "A" + "RT"]


def _repo(tmp_path: Path, text: str) -> Path:
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@example.org")
    git("config", "user.name", "tester")
    (tmp_path / "doc.md").write_text(text)
    git("add", "doc.md")
    git("commit", "-q", "-m", "add doc")
    return tmp_path


def test_clean_tree_is_green(tmp_path):
    hits, _ = release_guard.scan(_repo(tmp_path, "nothing to see\n"), FAKE_HASHES)
    assert hits == []


def test_guarded_term_in_tree_goes_red(tmp_path):
    hits, _ = release_guard.scan(_repo(tmp_path, f"a line with {FAKE} in it\n"), FAKE_HASHES)
    assert hits == [f"doc.md:1:{embargo.term_id(FAKE)}"]


def test_guarded_term_in_history_goes_red(tmp_path):
    root = _repo(tmp_path, f"{FAKE}\n")
    (root / "doc.md").write_text("clean now\n")
    subprocess.run(["git", "commit", "-qam", "scrub"], cwd=root, check=True)
    assert release_guard.scan(root, FAKE_HASHES)[0] == []
    hits, _ = release_guard.scan_history(root, FAKE_HASHES)
    assert any(h.endswith(embargo.term_id(FAKE)) for h in hits)


def test_whole_word_only():
    assert embargo.find("unzorblaxed", FAKE_HASHES) == []


def test_real_terms_are_on_the_list():
    for term in REAL:
        assert embargo.find(f"see {term} here"), term


def test_local_path_goes_red():
    assert embargo.find("/" + "Users/someone/file")


def test_this_repo_tree_is_clean():
    root = Path(__file__).resolve().parent.parent
    hits, _ = release_guard.scan(root)
    assert hits == []
