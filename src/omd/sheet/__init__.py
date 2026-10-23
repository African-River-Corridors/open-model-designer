"""omd.sheet — reusable FAST spreadsheet generator (house formatting + self-verify).

Domain-agnostic builder: a Python *spec* drives :class:`Workbook` to emit a FAST-structured,
self-calculating ``.xlsx`` in the house style, and :func:`verify` proves the live formulas
reproduce a Python source-of-truth.
"""

from . import formatting
from .verify import evaluate, verify
from .workbook import Calcs, Table, Workbook

__all__ = ["Calcs", "Table", "Workbook", "evaluate", "formatting", "verify"]
__version__ = "0.1.0"
