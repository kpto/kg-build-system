# Agent notes

Rules for working in this repository.

- Keep this file succinct: point form, human readable.
- A spec file is always finalised. No amendment trace: no "previously", "changed to", "to confirm",
  open-question sections, or leftover review comments.
- A spec file is always succinct.
- Domain models are always amnesic: frozen data holding only its own facts, with no reference to an
  owner, no identity stored that can be derived, and no behaviour needing the wider picture. That
  behaviour lives in functions beside the data.
