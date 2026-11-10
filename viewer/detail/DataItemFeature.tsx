"use client";

import { useMemo } from "react";

import { logicalTypeName } from "@/lib/expressions";
import {
  relationNamesFromRowSource,
  resolveAssetName,
  semanticSubjectKey,
} from "@/lib/indexes";
import type {
  DataField,
  ProjectionDTO,
  RelationDTO,
  RowSource,
} from "@/lib/types";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import { attachedMeaning } from "@/shared/design/meaning";
import { ConceptReferenceChip } from "@/shared/ui/ConceptReference";
import { activeDocument, documentSelection, type WorkspaceProps } from "@/workbench/types";
import { selectionForConceptTarget } from "@/workbench/conceptTarget";
import { DetailDocument, DetailEmptyState, DetailPanel } from "./view/DetailChrome";
import styles from "./detail.module.css";

type DataItemKind = "relation" | "projection";

function DataFieldRows({ columns }: { columns: DataField[] }) {
  if (!columns.length) return <DetailEmptyState>No columns are declared.</DetailEmptyState>;
  return (
    <div className={styles.fieldList}>
      {columns.map((column) => (
        <div key={column.name} className={styles.fieldRow}>
          <span className={styles.fieldKey}>{column.name}</span>
          <span className={styles.fieldType}>
            {logicalTypeName(column.logical_type)}
          </span>
          {column.description ? (
            <span className={styles.fieldDescription}>{column.description}</span>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function rowSourceSummary(source: RowSource): string {
  const relations = relationNamesFromRowSource(source);
  return [source.kind, relations.join(", ")].filter(Boolean).join(" · ");
}

export function DataItemEditor(props: WorkspaceProps) {
  const selection = documentSelection(activeDocument(props.state));
  const kind: DataItemKind =
    selection?.kind === "projection" ? "projection" : "relation";
  const name = selection?.component ?? selection?.name ?? "";
  const relation: RelationDTO | undefined =
    kind === "relation" ? props.state.index.relationByName.get(name) : undefined;
  const projection: ProjectionDTO | undefined =
    kind === "projection"
      ? props.state.index.projectionByName.get(name)
      : undefined;

  const model = useMemo(() => {
    const item = relation ?? projection;
    return {
      name: item?.name ?? name,
      description: item?.description,
      columns: item?.columns ?? [],
      assetName: resolveAssetName(props.state.index, name),
      rowSource: projection?.row_source,
      semantics:
        item?.semantics ??
        props.state.index.semanticsByKey.get(
          semanticSubjectKey(kind, name),
        )?.semantics,
    };
  }, [kind, name, projection, props.state.index, relation]);

  const concept = kind === "relation" ? "table" : "projection";
  const assetReference = model.assetName
    ? {
        concept: "asset" as const,
        name: model.assetName,
        target: { concept: "asset" as const, name: model.assetName },
      }
    : undefined;

  return (
    <DetailDocument
      testId="data-item-editor"
      concept={concept}
      kicker={`Design · ${concept}`}
      title={model.name || (kind === "relation" ? "Table" : "Projection")}
      subtitle={`${model.columns.length} columns${
        model.assetName ? ` · asset ${model.assetName}` : ""
      }`}
    >
      <DetailPanel concept={concept} title="Identity">
        <div className={styles.dataItemFacts}>
          <span>Kind</span>
          <strong>{concept}</strong>
          <span>Asset</span>
          {assetReference ? (
            <ConceptReferenceChip
              reference={assetReference}
              onOpen={() => {
                if (!assetReference.target) return;
                const target = selectionForConceptTarget(assetReference.target);
                if (target) props.actions.openTab({ selection: target, preview: true });
              }}
            />
          ) : (
            <strong>Unresolved</strong>
          )}
          <span>Columns</span>
          <strong>{model.columns.length}</strong>
          <span>Source</span>
          <strong>{model.description ?? "No description on this declaration."}</strong>
        </div>
      </DetailPanel>

      <DetailPanel concept="field" title="Columns" meta={`${model.columns.length}`}>
        <DataFieldRows columns={model.columns} />
      </DetailPanel>

      {model.rowSource ? (
        <DetailPanel concept="table" title="Row source">
          <p className={styles.dataItemRowSource}>
            {rowSourceSummary(model.rowSource)}
          </p>
        </DetailPanel>
      ) : null}

      <DetailPanel concept="semantics" title="Attached semantics">
        <DesignMeaning
          {...attachedMeaning(model.semantics)}
          emptyText="No meaning is attached to this declaration."
        />
      </DetailPanel>
    </DetailDocument>
  );
}
