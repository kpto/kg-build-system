/**
 * The mock-mode plan fixture.
 *
 * `src/lib/mock.ts` carries a document, an index, a catalogue, problems and a
 * status model — but no plan, and the shell has no plan fetch to fall back on. The
 * only honest stand-in for *compiled* output is compiled output, so this is the
 * verbatim `GET /api/plan` payload captured from the framework:
 *
 *     python -m studio_backend.compile_worker plan \
 *       --project-root reference_project --package reference_project \
 *       --module '{"import_module":"kg_build_system.modules.targets.file","class_qualname":"FileModule","configuration":{"relative_path":"graph.jsonl"}}' \
 *       --module '{"import_module":"kg_build_system.modules.targets.neo4j","class_qualname":"Neo4jModule","configuration":{}}' \
 *       --module '{"import_module":"kg_build_system.modules.targets.meta_graph","class_qualname":"MetaGraphModule","configuration":{}}' \
 *       --module '{"import_module":"kg_build_system.modules.operators.deduplication","class_qualname":"CollapseExactDuplicatesModule","configuration":{}}'
 *
 * 60 steps / 90 connections across five modules (core + one operator + three
 * targets), including the lowered SQL of 16 steps — enough volume to exercise the
 * layering, the module colours and the SQL sheet without a running backend.
 */

import type { StepPlan } from "./types";
import payload from "./samplePlan.json";

export const SAMPLE_PLAN: StepPlan = payload as unknown as StepPlan;
