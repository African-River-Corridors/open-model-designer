# OMD glossary

OMD is the shared machine that turns a project's inputs into a FAST-structured, self-checking workbook.
This glossary fixes the words used in the OMD design and in this repo.

## Language

### The machine and what it makes

**Open Model Designer (OMD)**:
The open-source model engine: the shared machine that takes a model's six inputs and produces the workbook and its checks.
_Avoid_: model kit, builder, engine (alone)

**Model library**:
A private collection of library modules and a house style profile, used with OMD.
_Avoid_: core library, the library repo's name (that is the repo, not the concept)

**Model**:
One project's use of OMD — for example a river-transport model or a power-plant model.
_Avoid_: workbook (the workbook is an output of a model), spec

**Oracle**:
The model's independent Python calculation of every line, which the workbook's formulas must reproduce.
_Avoid_: engine, sot, source of truth

**Engine core**:
What OMD owns with no deal or jurisdiction in it: timeline, sheet writing, calculation blocks, checking against the oracle, the check gates, style, provenance — plus a few universal finance primitives.
_Avoid_: core module

**Universal primitive**:
A calculation every model uses that has no deal or jurisdiction in it: balance roll-forward, straight-line depreciation, escalation, IRR, NPV.

### The six inputs to a model

**Timeline**:
The model's periodicity, horizon and start date, which sets the columns on every sheet.

**Assumptions**:
The values a model's logic reads, each with a unit and a source.
_Avoid_: inputs (inputs are all six), parameters

**Logic**:
The calculations that turn assumptions into results, written twice — once in the oracle and once as formulas.

**Outputs**:
The statements, figures and sheets a model must deliver to its readers.

**Checks**:
The conditions a model must pass to be trusted — reconciliations, baselines, tolerances — shown on the Checks sheet.

**Style**:
How a model looks: number formats, fonts, colours, unit labels and total layout.

### Reuse

**Module**:
A reusable unit of logic that declares what it consumes and what it produces, and carries its own oracle half, formula half and checks — for example national tax or debt sculpting.
_Avoid_: template (a template is bigger), block

**Library module**:
A module that is curated, reviewed and versioned in a module library rather than in one project; it may carry domain content such as a national tax.
_Avoid_: core module

**Project module**:
A module that lives in one model's repo; it may be promoted to a library later.

**Port**:
A named input a module needs or a named row it gives; wired to a model's rows, by standard line name unless the model overrides it.
_Avoid_: hook, link

**Jurisdiction file**:
One country's statutory values — tax rates, allowance classes, VAT and levies, withholding — each held as a dated rule with its legal source, read by every module for that country.
_Avoid_: tax table, statutory config

**Standard assumptions**:
A library's reusable, dated set of non-statutory assumption values — macro, finance defaults and starting unit costs — that a model inherits at a pinned date and may override, with each override shown.
_Avoid_: defaults (alone), base case

**Dated rule**:
A rule inside a module that holds from a stated date, so a change in law adds a rule and never edits an old one.

**Template**:
A starting model built from modules and a standard set of outputs — for example project finance — that a project copies and then edits.
_Avoid_: module, skeleton

### Standards

**Structure standard**:
The fixed rules every model obeys — FAST plus the house calculation-block form — enforced by the check gates and never optional.
_Avoid_: style, format

**Style profile**:
A named, swappable set of style choices. OMD's default profile carries the number and layout rules; an organisation's profile adds its branding.
_Avoid_: theme, template
