"use client";

/**
 * Graph declaration detail: the design's root contract read as a document.
 *
 * The Graph visualisation is a working surface; this document is the graph
 * declaration itself. Its banner states the graph's extent and the cards carry
 * the declared meaning and what the graph contains. It is not a record: it has
 * no Constitution, Properties, Connections or Bindings page.
 */

import { useMemo, type JSX } from "react";

import { effectiveLicenseForGraph } from "@/proof/license";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import { graphMeaning, meaningCount } from "@/shared/design/meaning";
import {
  activeDocument,
  documentSelection,
  type WorkspaceProps,
} from "@/workbench/types";
import {
  DetailBand,
  DetailDocument,
  type DetailFact,
} from "./view/DetailChrome";
import { InvolvedSteps } from "./view/InvolvedSteps";
import styles from "./detail.module.css";

export function GraphEditor(props: WorkspaceProps): JSX.Element {
  const index = props.state.index;
  const selection = documentSelection(activeDocument(props.state));
  const declaration = index.graphDeclaration;
  const name = declaration?.name ?? selection?.component ?? "Graph";
  const meaning = useMemo(() => graphMeaning(index), [index]);
  const license = useMemo(() => effectiveLicenseForGraph(index), [index]);
  const abstract = index.topologyNodes.filter((node) => node.abstract).length;
  const meaningTotal = meaningCount(meaning);

  const facts: DetailFact[] = [
    { label: "Nodes", value: `${index.topologyNodes.length}` },
    { label: "Abstract", value: `${abstract}` },
    { label: "Relations", value: `${index.topologyEdges.length}` },
    { label: "Meaning", value: `${meaningTotal}` },
    {
      label: "License",
      value: license.value,
      title: license.licenses.join(" · ") || "No asset declares a license.",
    },
  ];

  const coverage = [
    {
      key: "nodes",
      measure: "Nodes",
      count: index.topologyNodes.length,
      reading: "concrete and abstract graph participants",
    },
    {
      key: "abstract",
      measure: "Abstract",
      count: abstract,
      reading: "category nodes that group participants",
    },
    {
      key: "relations",
      measure: "Relations",
      count: index.topologyEdges.length,
      reading: "links between graph participants",
    },
    {
      key: "properties",
      measure: "Properties",
      count: index.stats.topologyProperties,
      reading: "declared on nodes and edges",
    },
    {
      key: "bindings",
      measure: "Bindings",
      count: index.stats.bindings,
      reading: "bindings that write the graph's records",
    },
  ];

  return (
    <DetailDocument
      testId="graph-editor"
      concept="graph"
      kicker="Graph"
      title={name}
      facts={facts}
    >
      {meaningTotal > 0 ? (
        <DetailBand
          title="Meaning"
          question="What is this graph for, and what does it exclude?"
          testId="graph-meaning"
        >
          <DesignMeaning
            purpose={meaning.purpose}
            claims={meaning.claims}
            limitations={meaning.limitations}
            frames={meaning.frames}
            emptyText="No graph purpose is attached."
          />
        </DetailBand>
      ) : null}

      <DetailBand
        title="Coverage"
        question="What does this graph contain?"
        testId="graph-coverage"
      >
        <ul className={styles.coverageList}>
          {coverage.map((row) => (
            <li key={row.key} className={styles.coverageItem}>
              <span className={styles.coverageMeasure}>{row.measure}</span>
              <span className={styles.coverageCount}>{row.count}</span>
              <span className={styles.coverageReading}>{row.reading}</span>
            </li>
          ))}
        </ul>
      </DetailBand>

      <InvolvedSteps index={index} selection={selection} />
    </DetailDocument>
  );
}
