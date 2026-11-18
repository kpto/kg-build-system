"use client";

import { useMemo } from "react";

import { expressionPreview, logicalTypeName, operationName } from "@/lib/expressions";
import {
  relationNamesFromRowSource,
  resolveAssetName,
  semanticSubjectKey,
} from "@/lib/indexes";
import type { ProjectionDTO, RelationDTO, ViewerIndex } from "@/lib/types";
import { effectiveLicense } from "@/proof/license";
import { Constitution } from "@/detail/view/Constitution";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import {
  constitutionModel,
} from "@/detail/model/constitution";
import { attachedMeaning } from "@/shared/design/meaning";
import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import {
  AssetPill,
  BindingPill,
  DerivedRelationPill,
  FieldPill,
} from "@/detail/view/ConceptPill";
import { activeDocument, documentSelection, type WorkspaceProps } from "@/workbench/types";
import {
  DetailBand,
  DetailDocument,
  MemberTable,
  type DetailFact,
  type MemberRow,
} from "./view/DetailChrome";
import styles from "./detail.module.css";
import { fieldDefinitionDetail, fieldDescription, recordSummary } from "@/lib/summary";

type DataItemKind = "relation" | "projection";

/** Derived relations that scan this relation directly, one level above. */
function derivedDependants(index: ViewerIndex, name: string) {
  return index.projections.filter(
    (projection) =>
      projection.name !== name &&
      relationNamesFromRowSource(projection.row_source).includes(name),
  );
}

/** Bindings that read this relation directly, not through another relation. */
function directBindings(index: ViewerIndex, name: string) {
  return index.bindings.filter((binding) =>
    relationNamesFromRowSource(binding.binding.rows).includes(name),
  );
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
      description: recordSummary(item ?? {}),
      definition: item?.definition,
      columns: item?.columns ?? [],
      assetName: resolveAssetName(index, name),
      rowSource: projection?.row_source,
      semantics:
        item?.meaning ??
        item?.semantics ??
        index.semanticsByKey.get(semanticSubjectKey(kind, name))?.semantics,
    };
  }, [index, kind, name, projection, relation]);

  const concept = kind === "relation" ? "table" : "projection";
  const license = effectiveLicense(index, model.assetName ? [model.assetName] : []);
  const derived = useMemo(
    () => derivedDependants(index, model.name),
    [index, model.name],
  );
  const bindings = useMemo(
    () => directBindings(index, model.name),
    [index, model.name],
  );

  const facts: DetailFact[] = [
    {
      label: "Asset",
      value: model.assetName ? (
        <AssetPill name={model.assetName} />
      ) : (
        "unresolved"
      ),
      absent: !model.assetName,
    },
  ];
  if (model.definition) {
    facts.push(
      { label: "Grain", value: model.definition.grain, wrap: true },
      {
        label: "Identity",
        value: model.definition.identity.join(", "),
        wrap: true,
        absent: !model.definition.identity.length,
      },
    );
  }
  if (model.rowSource) {
    facts.push({
      label: "Row source",
      value: model.rowSource.kind ?? "scan",
    });
  }
  facts.push({
    label: "License",
    value: license.value,
    title: license.licenses.join(" · ") || "No asset declares a license.",
  });

  const memberRows: MemberRow[] = model.columns.map((column) => ({
    key: column.name,
    cells: [
      <FieldPill
        name={column.name}
        component={model.name}
        ownerConcept={kind === "relation" ? "table" : "projection"}
      />,
      logicalTypeName(column.logical_type),
      column.definition ? fieldDefinitionDetail(column) : fieldDescription(column),
      column.expression
        ? operationName(column.expression) ??
          expressionPreview(column.expression, 0)
        : "reads the source",
    ],
  }));
  const dependantRows: MemberRow[] = [
    ...derived.map((projection) => ({
      key: `derived:${projection.name}`,
      cells: [
        <DerivedRelationPill
          key="dependant"
          name={projection.name}
          component={projection.name}
        />,
        "derived relation",
        `${projection.columns?.length ?? 0} columns`,
        "scans this relation",
      ],
    })),
    ...bindings.map((binding) => ({
      key: `binding:${binding.index}`,
      cells: [
        <BindingPill
          key="dependant"
          name={binding.binding.name ?? `binding #${binding.index}`}
          component={binding.component}
          ownerConcept={binding.kind}
          bindingIndex={binding.index}
        />,
        "binding",
        binding.component,
        "reads this relation directly",
      ],
    })),
  ];

  const meaning = attachedMeaning(model.semantics);
  const constitution = useMemo(
    () => constitutionModel(index, { level: kind, component: model.name }),
    [index, kind, model.name],
  );
  const constitutionSection = (
    <DetailBand
      concept="semantics"
      title="Constitution"
      question="What is this subject for, and how does it come to be?"
      testId="detail-constitution"
    >
      <Constitution model={constitution} />
    </DetailBand>
  );
  const hasMeaning =
    Boolean(meaning.purpose) ||
    meaning.claims.length > 0 ||
    meaning.limitations.length > 0 ||
    (meaning.frames?.length ?? 0) > 0;
  const meaningSection = hasMeaning ? (
      <DetailBand
        concept="semantics"
        title="Meaning"
        question="What is this for, and what does it exclude?"
        testId="detail-meaning"
      >
        <DesignMeaning
          {...meaning}
          emptyText="Meaning omitted for this declaration."
        />
      </DetailBand>

  ) : null;
  const membersSection = (
      <DetailBand
        concept="field"
        title="Members"
        question="Which columns does this relation publish?"
        testId="detail-columns"
      >
        <MemberTable
          columns={["Column", "Type", "Definition", "Expression"]}
          template="minmax(150px, 1.2fr) minmax(110px, 0.9fr) minmax(160px, 1.4fr) minmax(100px, 0.9fr)"
          rows={memberRows}
          empty="No columns are declared."
        />
      </DetailBand>

  );
  const dependantsSection = (
      <DetailBand
        concept={kind === "relation" ? "table" : "projection"}
        title="Dependants"
        question="Which layer depends on this relation?"
      >
        <MemberTable
          columns={["Dependant", "Kind", "Detail", "Relation"]}
          template="minmax(170px, 1.3fr) 100px minmax(120px, 1fr) minmax(120px, 1fr)"
          rows={dependantRows}
          empty="No derived relation or binding reads this relation directly."
        />
      </DetailBand>
  );

  return (
    <DetailDocument
      testId="data-item-editor"
      concept={concept}
      kicker={kind === "relation" ? "Source relation" : "Derived relation"}
      title={model.name || (kind === "relation" ? "Source relation" : "Derived relation")}
      subtitle={model.description}
      facts={facts}
    >
      {constitutionSection}
      {meaningSection}
      {membersSection}
      {dependantsSection}
    </DetailDocument>
  );
}
