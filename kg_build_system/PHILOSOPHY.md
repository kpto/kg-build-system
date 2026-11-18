# The philosophy of kg-build-system

Six principles, each stated with what it rules out. They are what the framework
enforces, not what it aspires to.

## 1. The declaration is the source of truth

Assets, relations, nodes, edges, bindings and properties are declared, and each
carries a `Meaning`: a purpose with its limitations, or explicit claims. A
declaration without meaning is a defect. Identity is a stable key; a display
label is never a key.

**Rules out:** behaviour that exists only in code. If the build does something
the declarations do not state, it is invisible, unauditable, and therefore
wrong rather than merely undocumented.

## 2. Artifacts are the currency; the dependency graph is the order

Steps consume and produce typed artifacts. Execution order follows artifact
dependencies, never the order in which planners were registered. Several
producers of one type coexist through openings (`validated`, `annotated`,
`projected`), so a pipeline is a chain of views over one type rather than a
mutation of it.

**Rules out:** "planned after" as a synonym for "runs after". Only an `Input`
creates an ordering. A step with no inputs is unordered by construction.

## 3. One component, one responsibility, one name

A planner plans; an executor executes; an instruction kind is typed; resources
are declared explicitly. A component's name states its single job —
`DumpSourcePlanner` reads a dump, `RecordGuardPlanner` vetoes malformed records,
`FilePlanner` writes files.

**Rules out:** god steps. A component called `graph_writer` that also applies
policy violates the philosophy twice: the name is wrong, and a framework
responsibility has been duplicated. Composition belongs in the dependency
graph — a subtraction, a join, a second writer — not inside a step.

## 4. Assets are untouched; adaptation is declared

The pinned source is the asset. The adapter is thin: it decodes, and it does not
select, map identities, join or aggregate. Every transformation is a relation
with a stated meaning, and caches are the adapter's business, recorded in a
manifest with digests.

**Rules out:** filters hidden in SQL and scripts that read a built file. Policy
kept inside a query is as opaque as policy kept inside a writer; it cannot be
named, inspected, re-run or diffed.

## 5. Extensibility is the design, not an escape hatch

When a capability is missing, add a planner and an executor and register them —
the same shape as the shipped ones. Interception of any stage is intended.

**Rules out:** side-car scripts. A program that runs after the build and edits
its output cannot be ordered, replayed, or inspected by the plan; it is outside
the contract no matter how useful it is.

## 6. The plan must read as the design

The workflow graph is documentation. If a behaviour is not a component, the
design does not include it, whatever the code does.

**Rules out:** claiming a capability that a reviewer cannot find in the plan.
"We prune uninformative edges" is only true if pruning is a step.

## Applying them

A design decision is complete when: the declaration states it; a named component
performs it; an artifact carries its result; the plan shows it; and a
reconciliation step fails the build when the outputs disagree.

Where a project breaks these, the repair is to move the responsibility to a
named place — not to rename the step that absorbed it.
