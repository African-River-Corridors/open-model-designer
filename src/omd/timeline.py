"""The timeline: periodicity, horizon and start date. It sets the columns on every sheet."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

PERIODS_PER_YEAR = {"monthly": 12, "quarterly": 4, "annual": 1}


class TimelineError(ValueError):
    pass


def _months_added(d: dt.date, months: int) -> dt.date:
    y, m = divmod(d.year * 12 + (d.month - 1) + months, 12)
    return dt.date(y, m + 1, 1)


@dataclass(frozen=True)
class Timeline:
    periodicity: str  # monthly | quarterly | annual
    periods: int
    start: dt.date  # first day of the first period

    def __post_init__(self) -> None:
        if self.periodicity not in PERIODS_PER_YEAR:
            raise TimelineError(
                f"periodicity {self.periodicity!r} is not one of {sorted(PERIODS_PER_YEAR)}"
            )
        if not isinstance(self.periods, int) or isinstance(self.periods, bool) or self.periods < 1:
            raise TimelineError(
                f"horizon must be a whole number of periods >= 1, got {self.periods!r}"
            )
        if self.start.day != 1:
            raise TimelineError(f"start {self.start} must be the first day of a period")
        if self.periodicity == "quarterly" and self.start.month not in (1, 4, 7, 10):
            raise TimelineError(f"a quarterly timeline must start on a quarter: got {self.start}")
        if self.periodicity == "annual" and self.start.month != 1:
            raise TimelineError(f"an annual timeline must start on 1 January: got {self.start}")

    @property
    def months_per_period(self) -> int:
        return 12 // PERIODS_PER_YEAR[self.periodicity]

    @classmethod
    def from_mapping(cls, m: dict) -> Timeline:
        """Build from the YAML `timeline:` block.

        periodicity: monthly | quarterly | annual
        start: 2027-01-01
        horizon_periods: 60      # or: horizon_years: 5   (exactly one)
        """
        unknown = set(m) - {"periodicity", "start", "horizon_periods", "horizon_years"}
        if unknown:
            raise TimelineError(f"unknown timeline key(s): {sorted(unknown)}")
        for key in ("periodicity", "start"):
            if key not in m:
                raise TimelineError(f"timeline needs {key!r}")
        has_p, has_y = "horizon_periods" in m, "horizon_years" in m
        if has_p == has_y:
            raise TimelineError("timeline needs exactly one of horizon_periods or horizon_years")
        start = m["start"]
        if isinstance(start, str):
            try:
                start = dt.date.fromisoformat(start)
            except ValueError as e:
                raise TimelineError(f"timeline start {start!r} is not an ISO date") from e
        if not isinstance(start, dt.date):
            raise TimelineError(f"timeline start {start!r} is not a date")
        per = m["periodicity"]
        if has_p:
            n = m["horizon_periods"]
        else:
            if per not in PERIODS_PER_YEAR:
                raise TimelineError(f"periodicity {per!r} is not one of {sorted(PERIODS_PER_YEAR)}")
            years = m["horizon_years"]
            if not isinstance(years, int) or isinstance(years, bool):
                raise TimelineError(f"horizon_years must be a whole number, got {years!r}")
            n = years * PERIODS_PER_YEAR[per]
        return cls(per, n, start)

    def period_start(self, i: int) -> dt.date:
        if not 0 <= i < self.periods:
            raise IndexError(i)
        return _months_added(self.start, i * self.months_per_period)

    def period_end(self, i: int) -> dt.date:
        return _months_added(self.start, (i + 1) * self.months_per_period) - dt.timedelta(days=1)

    def labels(self) -> list[str]:
        """Column headers: 2027-01 (monthly), 2027-Q1 (quarterly), 2027 (annual)."""
        out = []
        for i in range(self.periods):
            d = self.period_start(i)
            if self.periodicity == "monthly":
                out.append(f"{d.year}-{d.month:02d}")
            elif self.periodicity == "quarterly":
                out.append(f"{d.year}-Q{(d.month - 1) // 3 + 1}")
            else:
                out.append(str(d.year))
        return out
