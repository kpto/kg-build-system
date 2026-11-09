import { readFileSync } from "node:fs";
import { buildViewerIndex } from "../lib/indexes";
import { loadSnapshotFromObject } from "../lib/load";

/**
 * A small in-memory snapshot that exercises the current contract.
 *
 * It carries a graph declaration, an asset profile and attached semantics on
 * an asset, relation, projection, struct, field, node, edge, property and
 * binding. The five-megabyte Open Targets snapshot is not read here.
 */
const contractDocument = {
  format: "kg-viewer-snapshot",
  version: 1,
  name: "fixture-estate",
  title: "Fixture Estate Build",
  blueprint: {
    contract_extension: { generatedBy: "tests/fixtures.ts" },
    graph_declaration: {
      name: "fixture_graph",
      description: "A small graph used by the viewer contract tests.",
      semantics: {
        claims: [{ text: "The fixture graph contains one observed estate." }],
        purpose: {
          text: "Exercise the viewer data contract without loading a release.",
          frames: [
            {
              text: "The fixture is synthetic.",
              limitations: [{ text: "It is not production data." }],
            },
            {
              text: "Only one asset is represented.",
              limitations: [{ text: "No cross-asset joins are exercised." }],
            },
          ],
        },
      },
    },
    graph: {
      nodes: [
        {
          name: "documented",
          labels: ["Documented"],
          abstract: true,
          properties: [
            {
              name: "summary",
              logical_type: { kind: "unit", name: "str" },
              ref: ["topology", "property", "documented.summary"],
              annotations: [],
              semantics: {
                claims: [{ text: "The summary is a one-line rendering." }],
              },
            },
          ],
          annotations: [],
          description: "An abstract category with a summary property.",
          semantics: {
            claims: [{ text: "Every documented entity carries a summary." }],
            frames: [
              {
                text: "Documented entities are abstract.",
                limitations: [{ text: "No concrete descendant is bound." }],
              },
            ],
          },
        },
        {
          name: "defect",
          labels: ["Defect"],
          abstract: false,
          properties: [
            {
              name: "title",
              logical_type: { kind: "unit", name: "str" },
              ref: ["topology", "property", "defect.title"],
              annotations: [],
              description: "The defect title.",
              semantics: {
                claims: [{ text: "The title is the defect's display name." }],
              },
            },
          ],
          annotations: [],
          description: "A reported defect.",
          semantics: {
            claims: [{ text: "A defect is observed on an estate survey." }],
          },
          x_node_field: "survives",
        },
      ],
      edges: [
        {
          name: "has_observation",
          labels: ["HAS_OBSERVATION"],
          abstract: false,
          source: ["topology", "node", "documented"],
          target: ["topology", "node", "defect"],
          properties: [
            {
              name: "as_at",
              logical_type: { kind: "unit", name: "str" },
              ref: ["topology", "property", "has_observation.as_at"],
              annotations: [],
              semantics: {
                claims: [{ text: "The observation timestamp." }],
              },
            },
          ],
          annotations: [],
          description: "Links a documented entity to a defect.",
          semantics: {
            claims: [{ text: "The edge records when the defect was observed." }],
          },
        },
      ],
    },
    data: {
      relations: [
        {
          name: "surveys",
          asset: ["asset", "asset", "estate"],
          columns: [
            {
              name: "survey_id",
              logical_type: { kind: "unit", name: "str" },
              ref: ["data", "field", "surveys.survey_id"],
              annotations: [],
            },
            {
              name: "title",
              logical_type: { kind: "unit", name: "str" },
              ref: ["data", "field", "surveys.title"],
              annotations: [],
              semantics: {
                claims: [{ text: "The surveyor's description of the defect." }],
              },
            },
          ],
          annotations: [],
          description: "One survey row per defect.",
          semantics: {
            claims: [{ text: "The estate survey table." }],
          },
        },
      ],
      projections: [
        {
          name: "defect",
          columns: [
            {
              name: "defect_id",
              logical_type: { kind: "unit", name: "str" },
              ref: ["data", "field", "defect.defect_id"],
              annotations: [],
            },
            {
              name: "title",
              logical_type: { kind: "unit", name: "str" },
              ref: ["data", "field", "defect.title"],
              annotations: [],
              semantics: {
                claims: [{ text: "The projection keeps the survey title." }],
              },
            },
          ],
          annotations: [],
          description: "Defects ready for binding.",
          row_source: { kind: "scan", relation: ["data", "relation", "surveys"] },
          semantics: {
            claims: [{ text: "The defect projection scans the survey table." }],
          },
        },
      ],
      structs: [
        {
          name: "reading",
          columns: [
            {
              name: "value",
              logical_type: { kind: "unit", name: "float" },
              ref: ["data", "field", "reading.value"],
              annotations: [],
              semantics: {
                claims: [{ text: "A recorded measurement value." }],
              },
            },
          ],
          annotations: [],
          description: "A reading row shape.",
          semantics: {
            claims: [{ text: "The reading struct is an intermediate shape." }],
          },
        },
      ],
    },
    assets: [
      {
        name: "estate",
        website: null,
        version: "fixture-1",
        layout: {
          kind: "json",
          locator: "fixture://estate",
          format: "json",
          members: { surveys: "surveys.json" },
        },
        profile: {
          subject: "a monitored estate",
          coverage: "the estate survey table",
          authority: "primary",
          basis: "synthetic fixture data",
          title: "Fixture estate",
          description: "Not a real release.",
        },
        governance: { license: null, owner: null, metadata: {} },
        annotations: [],
        semantics: {
          claims: [{ text: "The fixture estate is a JSON asset." }],
          frames: [
            {
              text: "The asset is synthetic.",
              limitations: [{ text: "It has no release history." }],
            },
          ],
          x_semantics_field: "survives",
        },
        x_asset_field: "survives",
      },
    ],
    bindings: [
      {
        kind: "node",
        node: ["topology", "node", "defect"],
        identity: {
          kind: "field",
          field: ["data", "field", "surveys.survey_id"],
          path: [],
          logical_type: { kind: "unit", name: "str" },
        },
        source_identity: {
          kind: "field",
          field: ["data", "field", "surveys.survey_id"],
          path: [],
          logical_type: { kind: "unit", name: "str" },
        },
        target_identity: {
          kind: "field",
          field: ["data", "field", "defect.defect_id"],
          path: [],
          logical_type: { kind: "unit", name: "str" },
        },
        properties: {
          title: {
            kind: "field",
            field: ["data", "field", "surveys.title"],
            path: [],
            logical_type: { kind: "unit", name: "str" },
          },
        },
        rows: { kind: "scan", relation: ["data", "relation", "surveys"] },
        annotations: [],
        mode: "merge",
        debug_name: "defect.title",
        python_ref: {
          module: "fixture.bindings.defect",
          qualname: "DefectTitle",
          signature: "()",
        },
        semantics: {
          claims: [{ text: "The binding projects the survey title." }],
        },
      },
    ],
  },
  workflow: {
    components: [
      { id: "core", version: "1" },
      { id: "duckdb", version: "1" },
    ],
    steps: [
      {
        id: ["core", "binding.0"],
        inputs: [
          {
            opening_name: ["records"],
            type: ["duckdb", "source", "surveys"],
          },
        ],
        outputs: [
          {
            opening_name: ["output"],
            type: ["core", "binding", "defect", "0"],
          },
        ],
        instruction: { kind: ["sql", "duckdb"], payload: { sql: "SELECT 1" } },
      },
      {
        id: ["duckdb", "source.surveys"],
        outputs: [
          {
            opening_name: ["output"],
            type: ["duckdb", "source", "surveys"],
          },
        ],
        instruction: {
          kind: ["sql", "duckdb"],
          payload: { sql: "SELECT * FROM surveys" },
        },
      },
    ],
    connections: [
      {
        input: ["core", "binding.0", "input", "records"],
        output: ["duckdb", "source.surveys", "output", "output"],
      },
    ],
    provenance: { mode: "fixture" },
  },
  report: {
    published_artifacts: [],
    recovered_failures: [],
    unresolved_failures: [],
    provenance: { mode: "fixture" },
  },
};

export const contractSnapshot = loadSnapshotFromObject(contractDocument);
export const contractIndex = buildViewerIndex(contractSnapshot);

/**
 * The reference estate snapshot. It is kept under distinct names because older
 * viewer tests still import it; new contract tests use the fixture above.
 */
const referenceText = readFileSync(
  new URL("../public/data/reference.snapshot.json", import.meta.url),
  "utf8",
);

export const referenceSnapshot = loadSnapshotFromObject(JSON.parse(referenceText));
export const referenceIndex = buildViewerIndex(referenceSnapshot);

// Compatibility aliases for the restored viewer's remaining tests.
export const snapshot = referenceSnapshot;
export const index = referenceIndex;
