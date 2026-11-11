---
title: kg-build-system field guide
summary: A visual field guide to declaring, compiling and running a knowledge-graph build whose meaning survives it.
section: meta
order: 0
status: normative
verified: 2026-11-10
sources:
  - README.md
  - docs/developer/system-design.md
  - reference_project/
---

<div class="kb-hero">
  <p class="kb-kicker">kg-build-system · field guide</p>
  <div class="kb-display">Build a graph whose meaning survives the build.</div>
  <p class="kb-lede">Typed Python declarations become a checked blueprint, a workflow plan and published records. The model, the evidence and the limits travel with the result.</p>
  <div class="kb-actions">
    <a class="kb-button kb-button-primary" href="/start/walkthrough">Run the estate build</a>
    <a class="kb-button" href="/review/architecture">Review the model</a>
    <a class="kb-button" href="/reference/api">Look up a name</a>
  </div>
</div>

<!-- BEGIN GENERATED:status-strip -->
<div class="kb-stats"><span><b>354</b> tests</span><span><b>1957</b> subtests</span><span><b>1 error</b> pyright</span><span><b>2454d28</b> source</span><span><b>2026-11-11</b> checked</span></div>
<!-- END GENERATED:status-strip -->

<figure class="kb-plate">
  <img src="/_assets/system.svg" alt="A build moves from declarations through link, blueprint, plan and execute to published records, with an edit-time generation lane above.">
  <figcaption>The whole system on one page. Generation feeds declarations; three verbs take it from there.</figcaption>
</figure>

<a class="kb-band" href="/subjects/index">
  <span class="kb-band-kicker">Subject map</span>
  <strong>16 subjects, five perspectives</strong>
  <span>Every subject links its guide, binding spec, API view, philosophy and review evidence. Start with the map or go straight to the normative index.</span>
</a>

<a class="kb-band" href="/philosophy/index">
  <span class="kb-band-kicker">The lens</span>
  <strong>Philosophy: meaning before mechanism</strong>
  <span>Topology first, semantics as a hierarchy, explainability authored, the binding as a seam.</span>
</a>

## Two layers

<div class="kb-grid kb-layers">
  <a class="kb-card" href="/kernel/index"><span class="kb-num">Layer 1</span><h3>Kernel</h3><p>Domain-agnostic protocols and the extension surface: language, linker, planner, executor, runtime and resource provider.</p></a>
  <a class="kb-card" href="/framework/index"><span class="kb-num">Layer 2</span><h3>Framework</h3><p>The graph distribution and the authoring and review paths; the default distribution is one composition.</p></a>
</div>

## Three doors

<div class="kb-doors">
  <a class="kb-door" href="/start/index">
    <span class="kb-door-kicker">I want to build</span>
    <strong>Start with the estate</strong>
    <span>Install, run the reference build, then declare your own asset, rows, topology and bindings.</span>
  </a>
  <a class="kb-door" href="/review/index">
    <span class="kb-door-kicker">I want to judge</span>
    <strong>Review the model</strong>
    <span>Read the kernel boundary, the contracts, the product limits and the measured evidence.</span>
  </a>
  <a class="kb-door" href="/reference/index">
    <span class="kb-door-kicker">I know what I need</span>
    <strong>Look it up</strong>
    <span>Public names, the one CLI command, document shapes and the failure catalogue.</span>
  </a>
</div>

The default distribution is one composition of the kernel protocols; a new source, language, module or engine is a value passed to a `Toolchain`, and a new provider is added to the runtime.

## The guide

<div class="kb-grid">
  <a class="kb-card" href="/start/index"><span class="kb-num">01</span><h3>Start</h3><p>Install, run the full build, and place declarations in a project.</p></a>
  <a class="kb-card" href="/author/index"><span class="kb-num">02</span><h3>Author</h3><p>Asset, rows, values, grain, projections, topology, bindings and meaning.</p></a>
  <a class="kb-card" href="/pipeline/index"><span class="kb-num">03</span><h3>Pipeline</h3><p>Link declarations, assemble the blueprint, plan the work, execute it.</p></a>
  <a class="kb-card" href="/operate/index"><span class="kb-num">04</span><h3>Operate</h3><p>Publish, validate quality, debug a run, extend it and ship it.</p></a>
  <a class="kb-card" href="/review/index"><span class="kb-num">05</span><h3>Review</h3><p>Architecture, invariants, limits, decisions, verification and drift.</p></a>
  <a class="kb-card" href="/reference/index"><span class="kb-num">06</span><h3>Reference</h3><p>API surface, CLI, documents, failures and the glossary.</p></a>
</div>

## Two ways to read

- **Author path.** [Install](/start/install) → [walkthrough](/start/walkthrough) → [project shape](/start/project) → [Philosophy](/philosophy/index) → [Author](/author/index). The walkthrough is the shortest route to a published graph; Philosophy is the lens for changing it.
- **Review path.** [Philosophy](/philosophy/index) → [Architecture](/review/architecture) → [Contracts](/review/contracts) → [Limits](/review/limits) → [Verification](/review/verification) → [Drift](/review/drift). Evidence blocks are generated from the source checkout, not typed by hand.
- **Subject path.** [Subjects](/subjects/index) → pick one subject → switch between its guide, [spec](/spec/index), API, philosophy and review. The spec is the binding view; the guide explains it and the API names it.
- **Developer path.** [Framework philosophy](/developer/philosophy) → [System design](/developer/system-design) → [Data and expressions](/developer/data-and-expressions) → [Testing](/developer/testing) → [Reference](/reference/index).
- **Extension path.** [Operate](/operate/index) → [Extend](/operate/extend) → [Extension spec](/spec/extension) → [Developer system design](/developer/system-design) → [Review architecture](/review/architecture). A custom language, planner, executor or emitter composes a different `Toolchain`; a provider is added to the runtime.

> [!note] What this is not
> This guide describes one checkout, not a compatibility promise. The framework is experimental; there is no schema version, migration path or stable plan format. Recompile when a declaration, planner or executor changes.

<p class="kb-attribution">Interface choices follow <a href="https://lawsofux.com">Laws of UX</a> (Jon Yablonski). The mapping is in <a href="/review/design-notes">Design notes</a>.</p>
