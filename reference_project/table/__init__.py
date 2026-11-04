"""Logical contracts for the monitored-estate reference build.

The generated packages are produced by the ``@asset_contract`` declaration on
:class:`reference_project.assets.Estate`. They are checked in, imported by the
graph declarations, and never regenerated during a build.

The checked-in packages predate the single-asset request and keep their
historical per-table directories. A normal generation pass writes one package
at ``table/estate``; that multi-table product layout is a generation limit, not
a build input. This project is not regenerated during a build.
"""
