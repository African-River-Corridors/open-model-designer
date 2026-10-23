"""T0: modules are found automatically; a module that fails acceptance fails the CI command."""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from omd import acceptance
from omd.registry import DiscoveryError, discover

LEVY_SRC = Path(__file__).parent.parent / "src" / "omd" / "modules" / "levy.py"


def make_package(root: Path, name: str, files: dict[str, str]) -> None:
    pkg = root / name
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for fname, body in files.items():
        (pkg / fname).write_text(textwrap.dedent(body))


def levy_copy(root: Path, name: str, transform=lambda s: s) -> str:
    """A copy of the shipped toy module that imports from omd by absolute path."""
    return transform(LEVY_SRC.read_text().replace("from ..module", "from omd.module"))


def run_all(root: Path, pkg: str) -> subprocess.CompletedProcess:
    code = (
        f"import sys; sys.path.insert(0, {str(root)!r}); "
        f"from omd import acceptance; sys.exit(acceptance.main(['--all', {pkg!r}]))"
    )
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)


def test_the_shipped_modules_are_found_and_declare_their_ports_and_scope():
    """Discovery only, plus the cheap criteria (1 ports, 5 scope). The full five criteria run once per
    module in CI by `python -m omd.acceptance --all omd.modules` (in parallel) and in each module's own test."""
    mods = discover("omd.modules")
    assert "levy" in mods
    for name, m in mods.items():
        assert acceptance.check_module(m, {"1", "5"}) == [], name


def test_a_new_file_is_picked_up_with_no_registry_edit(tmp_path):
    make_package(tmp_path, "libA", {"one.py": levy_copy(tmp_path, "one")})
    (tmp_path / "libA" / "two.py").write_text(levy_copy(tmp_path, "two"))
    (tmp_path / "libA" / "_helper.py").write_text("X = 1\n")  # private: ignored
    sys.path.insert(0, str(tmp_path))
    try:
        assert sorted(discover("libA")) == ["one", "two"]
    finally:
        sys.path.remove(str(tmp_path))


def test_a_file_with_no_module_is_an_error_not_a_skip(tmp_path):
    make_package(tmp_path, "libB", {"stray.py": "X = 1\n"})
    sys.path.insert(0, str(tmp_path))
    try:
        with pytest.raises(DiscoveryError, match="no MODULE"):
            discover("libB")
    finally:
        sys.path.remove(str(tmp_path))


def test_the_ci_command_goes_green_on_good_modules(tmp_path):
    make_package(tmp_path, "libC", {"good.py": levy_copy(tmp_path, "good")})
    r = run_all(tmp_path, "libC")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 of 1 modules accepted" in r.stdout


def test_negative_control_a_broken_module_turns_the_ci_command_red(tmp_path):
    broken = levy_copy(tmp_path, "bad", lambda s: s.replace("r * rate", "r * rate * 2"))
    assert broken != levy_copy(tmp_path, "bad")  # the break is real
    make_package(tmp_path, "libD", {"good.py": levy_copy(tmp_path, "good"), "broken.py": broken})
    r = run_all(tmp_path, "libD")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "NOT ACCEPTED" in r.stdout and "1 of 2 modules accepted" in r.stdout


def test_an_empty_or_unknown_package_is_red(tmp_path):
    make_package(tmp_path, "libE", {})
    r = run_all(tmp_path, "libE")
    assert r.returncode == 1 and "no modules found" in r.stdout
