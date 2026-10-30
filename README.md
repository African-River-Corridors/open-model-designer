# OMD: Open Model Designer

OMD turns a financial model's six inputs into a FAST-structured workbook that checks itself.
It is a Python library and a set of tested finance modules. Status: **v0.1, alpha**. Licence: Apache-2.0.

Words used here are fixed in [GLOSSARY.md](GLOSSARY.md).

## The six inputs

A model is made of six things. OMD takes all six and writes the workbook.

1. **Timeline**: the periods, which set the columns on every sheet.
2. **Assumptions**: the values the logic reads, each with a unit and a source.
3. **Logic**: the calculations, written twice. Once in Python (the oracle). Once as live spreadsheet formulas.
4. **Outputs**: the statements and figures the model delivers.
5. **Checks**: rows that read zero when the model is right.
6. **Style**: the look of the workbook, so every model reads the same way.

The workbook follows the [FAST Standard](https://www.fast-standard.org). Each calculation sits in a block,
with its ingredients linked just above it.

## Modules

A module is one reusable piece of model logic: debt repayment, a cash waterfall, a tax engine, and so on.
The library holds 29 so far, in `src/omd/modules/`. They cover capex funding, interest during construction,
debt draw and repayment (linear, annuity, sculpted), cash sweeps, CFADS, cover ratios, a debt service reserve,
lock-up, tax pools and losses, a tax engine, VAT, working capital, take-or-pay revenue, a cash waterfall,
a distribution waterfall, FX conversion, returns, three statements, and scenarios. A project-finance template
(`omd.templates.project_finance`) composes them into one workbook.

A module declares its ports with units. It carries an oracle, the formulas, its own checks, a worked example,
a golden case and a scope note. A module is accepted only if it passes all six criteria (`omd.acceptance`):

1. Ports are declared, with units.
2. The oracle and the formulas agree on a worked example, and the formulas follow the input cells.
3. A golden case comes from an independent source, not from the module's own oracle.
4. The corruption audit is clean: every row the module writes is caught by one of its checks.
5. A scope note says what the module covers and what it does not.
6. The FAST audit of the worked-example book has no undeclared finding.

The golden cases are independent hand calculations by a reviewer agent that did not see the code.
The requests and the working are in [docs/golden-cases/](docs/golden-cases/).

## Install

```bash
pip install open-model-designer
```

The distribution is `open-model-designer`; the package you import is `omd`. (The name `omd` on PyPI belongs
to another project.) It is not on PyPI yet: until the first release, install from a clone with `uv sync`.

## Run it

```bash
uv sync
uv run pytest
uv run python -m omd.acceptance --all omd.modules
```

To check one module: `uv run python -m omd.acceptance omd.modules.cfads:MODULE`.

`omd.modules.levy` is the toy module that passes. `tests/test_acceptance.py` holds one failing fixture per criterion.

## How it was built

OMD was built with AI coding agents, under human review. The golden cases were calculated by separate agents
that did not see the code. A person reviews the design and the results.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
