"use client";

import { useMemo } from "react";

import { expressionPreview, logicalTypeName, operationName } from "@/lib/expressions";
import {
  relationNamesFromRowSource,
  resolveAssetName,
  semanticSubjectKey,
} from "@/lib/indexes";
import type {
  ProjectionDTO,
  RelationDTO,
  RowSource,
  ViewerIndex,
} from "@/lib/types";
import { effectiveLicense } from "@/proof/license";
import type { ProvenanceReferences } from "@/proof/references";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import { attachedMeaning } from "@/shared/design/meaning";
import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import { ConceptReferenceChip } from "@/shared/ui/ConceptReference";
import { activeDocument, documentSelection, type WorkspaceProps } from "@/workbench/types";
import { selectionForConceptTarget } from "@/workbench/conceptTarget";
import {
  DetailBand,
  DetailDocument,
  FactGrid,
  MemberTable,
  type DetailFact,
  type MemberRow,
} from "./view/DetailChrome";
import { FulfilmentMap, type AxisOpenTarget } from "./view/FulfilmentMap";
import {
  ExpressionTree,
  type ExpressionChain,
} from "./view/ExpressionTree";
import styles from "./detail.module.css";

type DataItemKind = "relation" | "projection";

function rowSourceSummary(source: RowSource): string {
  const relations = relationNamesFromRowSource(source);
  return [source.kind, relations.join(", ")].filter(Boolean).join(" · ");
}

function bindingsForRelation(
  index: ViewerIndex,
  name: string,
  projections: ProjectionDTO[],
) {
  const derivedThrough = new Set(
    projections
      .filter((projection) =>
        relationNamesFromRowSource(projection.row_source).includes(name),
      )
      .map((projection) => projection.name),
  );
  return index.bindings.filter((binding) => {
    const scanned = relationNamesFromRowSource(binding.binding.rows);
    return scanned.includes(name) || scanned.some((other) => derivedThrough.has(other));
  });
}

export function DataItemEditor(props: WorkspaceProps) {
  const index = props.state.index;
  const selection = documentSelection(activeDocument(props.state));
  const kind: DataItemKind =
    selection?.kind === "projection" ? "projection" : "relation";
  const name = selection?.component ?? selection?.name ?? "";
  const relation: RelationDTO | undefined =
    kind === "relation" ? index.relationByName.get(name) : undefined;
  const projection: ProjectionDTO | undefined =
    kind === "projection" ? index.projectionByName.get(name) : undefined;

  const model = useMemo(() => {
    const item = relation ?? projection;
    return {
      name: item?.name ?? name,
      description: item?.description,
      columns: item?.columns ?? [],
      assetName: resolveAssetName(index, name),
      rowSource: projection?.row_source,
      semantics:
        item?.semantics ??
        index.semanticsByKey.get(semanticSubjectKey(kind, name))?.semantics,
    };
  }, [index, kind, name, projection, relation]);

  const concept = kind === "relation" ? "table" : "projection";
  const assetReference = model.assetName
    ? {
        concept: "asset" as const,
        name: model.assetName,
        target: { concept: "asset" as const, name: model.assetName },
      }
    : undefined;
  const references = useMemo<ProvenanceReferences>(
    () => ({
      assets: model.assetName
        ? [
            {
              concept: "asset",
              name: model.assetName,
              target: { concept: "asset", name: model.assetName },
            },
          ]
        : [],
      tables:
        projection
          ? relationNamesFromRowSource(projection.row_source)
              .filter((scanned) => index.relationByName.has(scanned))
              .map((scanned) => ({
                concept: "table" as const,
                name: scanned,
                target: { concept: "table" as const, name: scanned },
              }))
          : [],
      projections: projection
        ? [
            ...relationNamesFromRowSource(projection.row_source)
              .filter((scanned) => index.projectionByName.has(scanned))
              .map((scanned) => ({
                concept: "projection" as const,
                name: scanned,
                target: { concept: "projection" as const, name: scanned },
              })),
          ]
        : [],
    }),
    [index, kind, model.assetName, model.name, projection],
  );
  const license = effectiveLicense(index, model.assetName ? [model.assetName] : []);
  const expressionChains = useMemo<ExpressionChain[]>(() => {
    if (kind !== "projection" || !projection) return [];
    return projection.columns.map((column) => ({
      id: `projection:${projection.name}.${column.name}`,
      target: {
        concept: "field" as const,
        label: column.name,
        detail: "derived column",
      },
      expression: column.expression,
    }));
  }, [kind, projection]);
  const bindings = useMemo(
    () => bindingsForRelation(index, model.name, index.projections),
    [index, model.name],
  );

  const openAxis = (target: AxisOpenTarget) => {
    switch (target.kind) {
      case "asset":
        props.actions.openTab({
          selection: {
            kind: "asset",
            level: "asset",
            name: target.name,
            component: target.name,
          },
          preview: true,
        });
        return;
      case "table":
        props.actions.openTab({
          selection: {
            kind: "relation",
            name: target.name,
            component: target.name,
          },
          preview: true,
        });
        return;
      case "projection":
        props.actions.openTab({
          selection: {
            kind: "projection",
            name: target.name,
            component: target.name,
          },
          preview: true,
        });
        return;
      case "node":
      case "edge":
        props.actions.openTab({
          selection: {
            kind: target.kind,
            level: target.kind,
            name: target.name,
            component: target.name,
          },
          preview: true,
        });
        return;
    }
  };

  const facts: DetailFact[] = [
    {
      label: "Kind",
      value: kind === "relation" ? "source relation" : "derived relation",
    },
    {
      label: "Asset",
      value: model.assetName ?? "unresolved",
      absent: !model.assetName,
      onOpen: model.assetName
        ? () => openAxis({ kind: "asset", name: model.assetName ?? "" })
        : undefined,
    },
    { label: "Columns", value: `${model.columns.length}` },
  ];
  if (model.rowSource) {
    facts.push(
      {
        label: "Row source",
        value: model.rowSource.kind ?? "scan",
      },
      {
        label: "Scans",
        value:
          relationNamesFromRowSource(model.rowSource).join(", ") ||
          "no relation",
        absent: !relationNamesFromRowSource(model.rowSource).length,
      },
    );
  }
  facts.push({
    label: "Bindings",
    value: `${bindings.length}`,
  });
  facts.push({
    label: "License",
    value: license.value,
    title: license.licenses.join(" · ") || "No asset declares a license.",
  });

  const memberRows: MemberRow[] = model.columns.map((column) => ({
    key: column.name,
    cells: [
      <span className={styles.memberName}>
        <ConceptGlyph concept="field" className={styles.memberGlyph} />
        {column.name}
      </span>,
      logicalTypeName(column.logical_type),
      column.description ?? "—",
      column.expression
        ? operationName(column.expression) ??
          expressionPreview(column.expression, 0)
        : "reads the source",
    ],
  }));

  const bindingRows: MemberRow[] = bindings.map((binding) => ({
    key: String(binding.index),
    onActivate: () =>
      openAxis({ kind: binding.kind, name: binding.component }),
    title: `Open ${binding.kind} ${binding.component}`,
    cells: [
      <span className={styles.memberName}>
        <ConceptGlyph concept={binding.kind} className={styles.memberGlyph} />
        {binding.binding.name ?? `binding #${binding.index}`}
      </span>,
      binding.kind,
      `${Object.keys(binding.binding.properties ?? {}).length}`,
      relationNamesFromRowSource(binding.binding.rows).join(", ") || "—",
    ],
  }));

  const stepRows: MemberRow[] = bindings
    .filter((binding) => binding.step)
    .map((binding) => ({
      key: `${binding.index}:step`,
      cells: [
        binding.step ? `${binding.step.id[0]}.${binding.step.id[1]}` : "—",
        binding.component,
        binding.step?.instruction.kind?.join(":") ?? "unknown",
        `${binding.index}`,
      ],
    }));

  const meaning = attachedMeaning(model.semantics);
  const meaningLimitationCount =
    meaning.limitations.length +
    (meaning.frames ?? []).reduce(
      (total, frame) => total + (frame.limitations?.length ?? 0),
      0,
    );

  return (
    <DetailDocument
      testId="data-item-editor"
      concept={concept}
      kicker={`Design · ${kind === "relation" ? "source relation" : "derived relation"}`}
      title={model.name || (kind === "relation" ? "Source relation" : "Derived relation")}
      subtitle={`${model.columns.length} columns${
        model.assetName ? ` · asset ${model.assetName}` : ""
      }`}
      license={{
        value: license.value,
        source: license.source,
        title: license.licenses.join(" · ") || "No asset declares a license.",
      }}
    >
      <DetailBand
        concept={concept}
        title="Overview"
        question="What is this relation, in one screen?"
        meta={model.name}
      >
        {model.description ? (
          <p className={styles.bandNote}>{model.description}</p>
        ) : null}
        <FactGrid facts={facts} />
      </DetailBand>

      <DetailBand
        concept="semantics"
        title="Meaning"
        question="What is this relation for, and what does it exclude?"
        meta={`${meaning.claims.length} ${
          meaning.claims.length === 1 ? "claim" : "claims"
        } · ${meaningLimitationCount} ${
          meaningLimitationCount === 1 ? "limitation" : "limitations"
        }`}
      >
        <DesignMeaning
          {...meaning}
          emptyText="No meaning is attached to this declaration."
        />
      </DetailBand>

      <DetailBand
        title="Fulfilment"
        question="Which record does this relation fulfil?"
        meta={`${bindings.length} ${bindings.length === 1 ? "binding" : "bindings"}`}
        testId="detail-fulfilment"
      >
        <FulfilmentMap
          index={index}
          subject={{ kind, component: model.name }}
          onOpen={openAxis}
        />
      </DetailBand>

      <DetailBand
        concept="graph"
        title="Sources"
        question="Where does this relation read from?"
        meta={`${model.assetName ? 1 : 0} ${
          model.assetName ? "asset" : "assets"
        } · ${references.tables.length} ${
          references.tables.length === 1 ? "source relation" : "source relations"
        }`}
      >
        <div className={styles.sourcesGrid}>
          <div className={styles.sourcesGroup}>
            <p className={styles.sourcesLabel}>
              <span>
                <ConceptGlyph concept="asset" className={styles.provenanceGroupIcon} />{" "}
                Assets
              </span>
              <span>{references.assets.length}</span>
            </p>
            {assetReference ? (
              <div className={styles.provenanceItems}>
                <ConceptReferenceChip
                  reference={assetReference}
                  showIcon={false}
                  onOpen={() => {
                    const target = selectionForConceptTarget(assetReference.target);
                    if (target) {
                      props.actions.openTab({ selection: target, preview: true });
                    }
                  }}
                />
              </div>
            ) : (
              <p className={styles.provenanceEmpty}>None resolved</p>
            )}
          </div>
          <div className={styles.sourcesGroup}>
            <p className={styles.sourcesLabel}>
              <span>
                <ConceptGlyph concept="table" className={styles.provenanceGroupIcon} />{" "}
                Source relations
              </span>
              <span>{references.tables.length}</span>
            </p>
            <div className={styles.provenanceItems}>
              {references.tables.length ? (
                references.tables.map((reference) => (
                  <ConceptReferenceChip
                    key={`${reference.concept}:${reference.name}`}
                    reference={reference}
                    showIcon={false}
                    onOpen={
                      reference.target
                        ? () => {
                            const target = selectionForConceptTarget(
                              reference.target!,
                            );
                            if (target) {
                              props.actions.openTab({ selection: target, preview: true });
                            }
                          }
                        : undefined
                    }
                  />
                ))
              ) : (
                <p className={styles.provenanceEmpty}>None resolved</p>
              )}
            </div>
          </div>
          <div className={styles.sourcesGroup}>
            <p className={styles.sourcesLabel}>
              <span>
                <ConceptGlyph concept="projection" className={styles.provenanceGroupIcon} />{" "}
                Derived relations
              </span>
              <span>{references.projections.length}</span>
            </p>
            <div className={styles.provenanceItems}>
              {references.projections.length ? (
                references.projections.map((reference) => (
                  <ConceptReferenceChip
                    key={`${reference.concept}:${reference.name}`}
                    reference={reference}
                    showIcon={false}
                    onOpen={
                      reference.target
                        ? () => {
                            const target = selectionForConceptTarget(
                              reference.target!,
                            );
                            if (target) {
                              props.actions.openTab({ selection: target, preview: true });
                            }
                          }
                        : undefined
                    }
                  />
                ))
              ) : (
                <p className={styles.provenanceEmpty}>None resolved</p>
              )}
            </div>
          </div>
        </div>
      </DetailBand>

      <DetailBand
        concept="workflow"
        title="Build steps"
        question="Which steps read this relation?"
        meta={`${stepRows.length} ${stepRows.length === 1 ? "consumer" : "consumers"}`}
      >
        {stepRows.length ? (
          <MemberTable
            columns={["Step", "Record", "Instruction", "Binding"]}
            template="minmax(160px, 1.2fr) minmax(110px, 0.9fr) minmax(100px, 0.8fr) 60px"
            rows={stepRows}
            empty="No step reads this relation."
          />
        ) : model.rowSource ? (
          <p className={styles.inlineEmpty}>
            {rowSourceSummary(model.rowSource)}. The plan that computes this
            relation is shown on the record that binds it.
          </p>
        ) : (
          <p className={styles.inlineEmpty}>
            A source relation reads its asset; no build step is declared on the
            declaration itself.
          </p>
        )}
      </DetailBand>

      {kind === "projection" ? (
        <ExpressionTree
          index={index}
          references={references}
          item={{ concept, label: model.name }}
          fields={model.columns.map((column) => column.name)}
          chains={expressionChains}
        />
      ) : (
        <DetailBand
          concept="graph"
          title="Expression"
          question="Which fields and operations produce the value?"
          meta="source"
        >
          <p className={styles.inlineEmpty}>
            A source relation reads one asset field per output. It has no
            computed expression; its adaptations belong to a derived relation.
          </p>
        </DetailBand>
      )}

      <DetailBand
        concept="field"
        title="Members"
        question="Which columns does this relation publish?"
        meta={`${model.columns.length}`}
        testId="detail-columns"
      >
        <MemberTable
          columns={["Column", "Type", "Definition", "Expression"]}
          template="minmax(150px, 1.2fr) minmax(110px, 0.9fr) minmax(160px, 1.4fr) minmax(100px, 0.9fr)"
          rows={memberRows}
          empty="No columns are declared."
        />
      </DetailBand>

      <DetailBand
        concept={kind === "relation" ? "node" : "projection"}
        title="Bindings"
        question="Which record does this relation fulfil?"
        meta={`${bindingRows.length}`}
      >
        <MemberTable
          columns={["Binding", "Record kind", "Writes", "Rows read"]}
          template="minmax(170px, 1.3fr) 100px 64px minmax(130px, 1.1fr)"
          rows={bindingRows}
          empty="No binding reads this relation."
        />
      </DetailBand>
    </DetailDocument>
  );
}
