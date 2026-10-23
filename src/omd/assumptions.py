"""Assumptions as YAML, each with provenance. A missing source fails the build.

A model's assumptions file::

    timeline: {periodicity: monthly, start: 2027-01-01, horizon_years: 5}
    inherit: {from: standard.yaml, as_of: 2027-01-01}   # optional, see StandardSet
    assumptions:
      unit_price:
        value: 12.5
        unit: USD/tonne
        label: Unit price
        source: Supplier quote Q-104
        date: 2026-09-30
        who: A. Person
        estimate: false

Every assumption needs value, unit, label, source, date, who and an `estimate` flag. A missing or
blank field is an error that names the key and the field, and every error is listed at once.

A case is a YAML delta over the base: it names the keys it changes and nothing else. A changed
value must come with its own source, because the old source did not say the new number.

    case: base
    set:
      unit_price: {value: 14.0, source: Revised quote Q-117}   # a new value needs its own source
      volume: {value: 9, source: Revised plan, date: 2026-10-01, who: A. Person}

Standard assumptions (structure only here; the values belong to a library) are dated: each key
holds a list of values with the date each holds from. A model inherits the set at a pinned date and
may override; `AssumptionSet.overrides` lists every override with the standard value it replaced.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from .timeline import Timeline

FIELDS = ("value", "unit", "label", "source", "date", "who", "estimate")
PROVENANCE = ("unit", "label", "source", "date", "who", "estimate")


class AssumptionsError(ValueError):
    """The assumptions are invalid. `problems` lists every one."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


class _StrictLoader(yaml.SafeLoader):
    """A YAML loader that refuses a repeated key instead of keeping the last."""


def _no_dupes(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dupes)


def load_yaml(source: str | Path) -> Any:
    """Parse YAML text or a file path. Repeated keys raise."""
    text = Path(source).read_text() if isinstance(source, Path) else source
    try:
        return yaml.load(text, Loader=_StrictLoader)  # noqa: S506 — SafeLoader subclass
    except yaml.YAMLError as e:
        raise AssumptionsError([f"invalid YAML: {e}"]) from e


@dataclass(frozen=True)
class Assumption:
    key: str
    value: float
    unit: str
    label: str
    source: str
    date: dt.date
    who: str
    estimate: bool


@dataclass(frozen=True)
class Override:
    key: str
    standard_value: float
    value: float
    standard_source: str
    source: str


@dataclass(frozen=True)
class AssumptionSet:
    items: dict[str, Assumption]
    timeline: Timeline | None = None
    overrides: tuple[Override, ...] = field(default_factory=tuple)
    inherited: frozenset[str] = frozenset()

    def __getitem__(self, key: str) -> Assumption:
        return self.items[key]

    def values(self) -> dict[str, float]:
        return {k: a.value for k, a in self.items.items()}

    def override_report(self) -> str:
        """The overrides of the inherited standard, one per line (empty if none)."""
        return "\n".join(
            f"{o.key}: standard {o.standard_value:g} ({o.standard_source}) -> {o.value:g} ({o.source})"
            for o in self.overrides
        )


def _date(v: Any) -> dt.date | None:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        try:
            return dt.date.fromisoformat(v)
        except ValueError:
            return None
    return None


PLACEHOLDERS = frozenset({"tbc", "tbd", "-", "--", "n/a", "na", "none", "?", "todo"})


def _blank(v: Any) -> bool:
    """Nothing there, or only a placeholder where a real source or name belongs."""
    return v is None or (
        isinstance(v, str) and (not v.strip() or v.strip().lower() in PLACEHOLDERS)
    )


def parse_assumption(key: str, raw: Any, problems: list[str]) -> Assumption | None:
    """Validate one entry; append every problem found and return None if there is any."""
    if not isinstance(raw, dict):
        problems.append(f"{key}: must be a mapping with {', '.join(FIELDS)}")
        return None
    start = len(problems)
    unknown = set(raw) - set(FIELDS)
    if unknown:
        problems.append(f"{key}: unknown field(s) {sorted(unknown)}")
    for f in FIELDS:
        if f not in raw or (f != "estimate" and _blank(raw[f])):
            problems.append(f"{key}: missing {f}")
    v = raw.get("value")
    if "value" in raw and (
        not isinstance(v, int | float) or isinstance(v, bool) or not math.isfinite(v)
    ):
        problems.append(f"{key}: value must be a finite number, got {v!r}")
    d = _date(raw.get("date"))
    if "date" in raw and not _blank(raw["date"]) and d is None:
        problems.append(f"{key}: date {raw['date']!r} is not an ISO date")
    if "estimate" in raw and not isinstance(raw["estimate"], bool):
        problems.append(f"{key}: estimate must be true or false, got {raw['estimate']!r}")
    if len(problems) > start:
        return None
    return Assumption(
        key,
        float(v),
        str(raw["unit"]).strip(),
        str(raw["label"]).strip(),
        str(raw["source"]).strip(),
        d,
        str(raw["who"]).strip(),
        raw["estimate"],
    )


def parse_assumptions(block: Any) -> dict[str, Assumption]:
    problems: list[str] = []
    if not isinstance(block, dict) or not block:
        raise AssumptionsError(["assumptions: must be a non-empty mapping"])
    out = {}
    for key, raw in block.items():
        a = parse_assumption(str(key), raw, problems)
        if a is not None:
            out[a.key] = a
    if problems:
        raise AssumptionsError(problems)
    return out


# --- standard assumptions: dated values, inherited at a pinned date -----------------------------
@dataclass(frozen=True)
class StandardSet:
    """A library's dated set. key -> entries sorted by the date each holds from."""

    entries: dict[str, tuple[tuple[dt.date, Assumption], ...]]

    @classmethod
    def parse(cls, doc: Any) -> StandardSet:
        problems: list[str] = []
        block = (doc or {}).get("standard") if isinstance(doc, dict) else None
        if not isinstance(block, dict) or not block:
            raise AssumptionsError(["standard: must be a non-empty mapping"])
        out = {}
        for key, rules in block.items():
            if not isinstance(rules, list) or not rules:
                problems.append(f"{key}: needs a list of dated values")
                continue
            dated = []
            for i, raw in enumerate(rules):
                if not isinstance(raw, dict) or _date(raw.get("from")) is None:
                    problems.append(f"{key}[{i}]: needs `from` (ISO date)")
                    continue
                body = {k: v for k, v in raw.items() if k != "from"}
                a = parse_assumption(f"{key}[{i}]", body, problems)
                if a is not None:
                    dated.append((_date(raw["from"]), replace(a, key=str(key))))
            out[str(key)] = tuple(sorted(dated, key=lambda t: t[0]))
        if problems:
            raise AssumptionsError(problems)
        return cls(out)

    def at(self, as_of: dt.date) -> dict[str, Assumption]:
        """Each key's value as it held on `as_of`. A key with no value yet is an error."""
        out, problems = {}, []
        for key, dated in self.entries.items():
            held = [a for d, a in dated if d <= as_of]
            if not held:
                problems.append(f"{key}: no value holds on {as_of} (first from {dated[0][0]})")
            else:
                out[key] = held[-1]
        if problems:
            raise AssumptionsError(problems)
        return out


def build_set(
    doc: Any, *, base_dir: Path | None = None, standard: StandardSet | None = None
) -> AssumptionSet:
    """A model's assumptions from its parsed YAML document."""
    if not isinstance(doc, dict):
        raise AssumptionsError(["the assumptions file must be a mapping"])
    unknown = set(doc) - {"timeline", "inherit", "assumptions"}
    if unknown:
        raise AssumptionsError([f"unknown top-level key(s): {sorted(unknown)}"])
    timeline = Timeline.from_mapping(doc["timeline"]) if "timeline" in doc else None

    items: dict[str, Assumption] = {}
    inherited: set[str] = set()
    overrides: list[Override] = []
    inh = doc.get("inherit")
    if inh is not None:
        if standard is None:
            if not isinstance(inh, dict) or "from" not in inh:
                raise AssumptionsError(["inherit: needs `from` (a standard-assumptions file)"])
            path = Path(inh["from"])
            path = path if path.is_absolute() or base_dir is None else base_dir / path
            standard = StandardSet.parse(load_yaml(path))
        as_of = _date(inh.get("as_of")) if isinstance(inh, dict) else None
        if as_of is None:
            raise AssumptionsError(["inherit: needs `as_of` (the pinned ISO date)"])
        items.update(standard.at(as_of))
        inherited = set(items)

    own = parse_assumptions(doc["assumptions"]) if "assumptions" in doc else {}
    for key, a in own.items():
        if key in inherited:
            std = items[key]
            overrides.append(Override(key, std.value, a.value, std.source, a.source))
        items[key] = a
    if not items:
        raise AssumptionsError(["no assumptions: give `assumptions` or `inherit`"])
    return AssumptionSet(items, timeline, tuple(overrides), frozenset(inherited - set(own)))


def load_assumptions(path: str | Path) -> AssumptionSet:
    path = Path(path)
    return build_set(load_yaml(path), base_dir=path.parent)


# --- cases: YAML deltas over a base --------------------------------------------------------------
def apply_case(base: AssumptionSet, case_doc: Any) -> AssumptionSet:
    """Apply a case delta. Only the keys it names change; an unknown key is an error."""
    if not isinstance(case_doc, dict) or "set" not in case_doc:
        raise AssumptionsError(["a case needs a `set` mapping"])
    unknown = set(case_doc) - {"case", "set"}
    if unknown:
        raise AssumptionsError([f"unknown case key(s): {sorted(unknown)}"])
    delta = case_doc["set"]
    if not isinstance(delta, dict) or not delta:
        raise AssumptionsError(["case: `set` must be a non-empty mapping"])
    problems: list[str] = []
    items = dict(base.items)
    overrides = {o.key: o for o in base.overrides}
    inherited = set(base.inherited)
    for key, change in delta.items():
        if key not in items:
            problems.append(f"case: {key!r} is not an assumption in the base")
            continue
        if not isinstance(change, dict):
            change = {"value": change}
        bad = set(change) - set(FIELDS)
        if bad:
            problems.append(f"case {key}: unknown field(s) {sorted(bad)}")
            continue
        old = items[key]
        merged = {f: getattr(old, f) for f in FIELDS} | change
        a = parse_assumption(key, merged, problems)
        if a is None:
            continue
        if a.value != old.value and a.source == old.source:
            problems.append(
                f"case {key}: the value changes from {old.value:g} to {a.value:g}, so the case "
                f"must give its own source (the old source, {old.source!r}, did not say {a.value:g})"
            )
            continue
        items[key] = a
        if a.value != old.value:
            if key in overrides:
                o = overrides[key]
                overrides[key] = Override(
                    key, o.standard_value, a.value, o.standard_source, a.source
                )
            elif key in inherited:
                overrides[key] = Override(key, old.value, a.value, old.source, a.source)
            inherited.discard(key)
    if problems:
        raise AssumptionsError(problems)
    return replace(
        base, items=items, overrides=tuple(overrides.values()), inherited=frozenset(inherited)
    )


def load_case(base: AssumptionSet, path: str | Path) -> AssumptionSet:
    return apply_case(base, load_yaml(Path(path)))


# --- into a workbook -----------------------------------------------------------------------------
def write_inputs(wb, aset: AssumptionSet, *, section: str = "Assumptions") -> dict[str, str]:
    """Write the assumptions onto the Inputs sheet with their provenance beside each value.

    Returns {key: cell ref} for use in formulas. Columns: A label with its unit, B value, C unit, D source,
    E date, F who, G "ESTIMATE" for an estimate.
    """
    refs = wb.inputs(
        section,
        {k: (wb.style.unit_label(a.label, a.unit), a.value) for k, a in aset.items.items()},
    )
    ws = wb.inputs_sheet
    for key, a in aset.items.items():
        row = int(refs[key].rsplit("$", 1)[1])
        ws.cell(row=row, column=3, value=a.unit)
        ws.cell(row=row, column=4, value=a.source)
        ws.cell(row=row, column=5, value=a.date.isoformat())
        ws.cell(row=row, column=6, value=a.who)
        if a.estimate:
            ws.cell(row=row, column=7, value="ESTIMATE")
    return refs
