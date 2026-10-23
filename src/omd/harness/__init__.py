"""The model harness: FAST calculation blocks, the driver tree, and the audits.

`fastblock` and `drivertree` build a model. `readchecks`, `audit_checks`, `audit_inputs` and
`audit_fast` read a built workbook back. Every audit is a function that takes the model-specific
facts (sheet names, target rows, check predicates) as arguments; none holds a model's data.
"""
