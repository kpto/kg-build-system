# Relation Reuse Boundaries — Proposed

## Status

Proposed, **not implemented**. Nothing in the current build materialises the
graph aggregation. The trade-off is recorded here so the decision is made
deliberately rather than by accumulation.

## The problem

Core exposes every intermediate relation as a DuckDB *view*: one per bound
source table, one per projection, one per binding, one per graph aggregation.
Views are inlined into whatever consumes them, so each consumer independently
re-executes the upstream pipeline — source file re-read, expansions re-run,
projections recomputed.

The spec keeps them lazy on purpose, and for a single narrow consumer that is
the right call: DuckDB pushes the consumer's projection list and filters down
into the physical scan, and nothing is written to disk that nobody asked for.

The cost appears at fan-out. One aggregation may feed an operator, the file
target, the Neo4j target, and an observation module. Each pays the full
pipeline. Build cost is roughly consumers x pipeline, and adding a read-only
diagnostic module raises it again.

## Evidence

Measured on a 240,000-row aggregate built from a nested JSON feed behind the
same shape of lazy views core produces:

| query | lazy view | physical table |
|---|---|---|
| `SELECT COUNT(*)` | 202 ms | 0.00 s |
| `SELECT * … ORDER BY ALL LIMIT 200` | 198 ms | 0.03 s |

A physical table answers a count from row-group metadata. A view cannot: the
rows have to exist before they can be counted. The gap is the whole argument.

Two related measurements bound the alternatives:

- a top-`N` sort retains only `LIMIT` rows — 9.6 MB of spill at forty million
  rows. Reading everything is not the same as holding everything.
- `COUNT(*) OVER ()` must materialise its input to know the total: 9.8 s and
  roughly 1.9 GB of temporary files on the same forty million rows. Folding a
  count into a sample with a window function converts a bounded query into an
  unbounded one.

## What already exists

`RelationService.materialize(name, query)` creates a private backing table and
publishes it under the same public view shape, and the executor checkpoints
after any step that materialised. Consuming modules cannot tell the difference.
The deduplication and merging operators already use it, so a build with an
operator configured has its graph materialised once and shared; a build with
only targets and diagnostics does not.

So the mechanism is not missing. What is missing is a rule for when core should
ask for it.

## Options

**A. Materialise on fan-out, decided at compile time.** The workflow contract
already records every connection. An output read by two or more steps is
a reuse boundary by definition, and the decision needs no runtime information.
Core's aggregation steps would materialise whenever `len(consumers) > 1` and stay
lazy otherwise. This is the option this document recommends.

**B. A runtime policy.** `BuildRuntime` gains a flag or a row-count threshold.
A row-count threshold is self-defeating — counting a lazy view is the expensive
operation being avoided. A blunt flag moves a per-dataset decision into global
configuration.

**C. Per-consumer opt-in.** Any consumer could request materialisation of an
input it received. Too late: the first consumer has already run the pipeline.

## Costs of recommending A

Materialising the aggregation forces full generation of rows a lazy consumer
might never have produced, and writes the whole graph to disk. For a build whose
only consumers are a Neo4j export per component and one file write, laziness may
still win.

Disk and spill therefore become the binding constraint, and the runtime already
exposes the knobs — `duckdb_storage`, `duckdb_memory_limit`, and the working
directory that backs spill. A reuse boundary makes them matter in a way a purely
lazy build does not.

Checkpointing is the other cost. The relation service checkpoints once after each
step that materialised, so the boundary step pays a write the lazy path avoids.

## Open questions

- Does the fan-out rule apply below the graph level, where projections are often
  consumed once? Applying it uniformly would materialise a lot for no gain.
- Should the rule count consumers, or consumers that read most columns? A
  consumer selecting two of forty columns benefits far less from reuse.
- Where should spill live for a large materialised graph: the working directory,
  the build temp directory, or a caller-supplied path?

## Out of scope

Incremental and cached builds across runs, persisted statistics, and any
target-side reuse. None of them change the observation above: within a single
build, a lazy view is re-executed per consumer.
