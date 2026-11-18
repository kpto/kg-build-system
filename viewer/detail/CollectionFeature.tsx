"use client";

/**
 * A virtual collection document: one layer read as a group.
 *
 * The pages are Constitution (the layer DAG below, drawn with the same DAG as a
 * participant), Contribution (one layer above), Items (the members of the
 * layer) and Coverage. A collection has no Meaning page: it declares no purpose
 * of its own.
 */

import { useMemo } from "react";

import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import { ConceptPill } from "@/detail/view/ConceptPill";
import { Constitution } from "@/detail/view/Constitution";
import { activeDocument, documentSelection, type WorkspaceProps } from "@/workbench/types";
import {
  collectionDagModel,
  collectionModel,
  type CollectionItem,
  type CollectionRef,
} from "./model/collection";
import {
  DetailBand,
  DetailDocument,
  MemberTable,
  type MemberRow,
} from "./view/DetailChrome";
import styles from "./detail.module.css";

function openCollection(props: WorkspaceProps, ref: CollectionRef): void {
  props.actions.openTab({
    selection: {
      kind: "collection",
      collection: ref.id,
      component: ref.component,
      name: ref.component,
    },
    preview: true,
  });
}

function ItemLabel({
  item,
  onOpen,
}: {
  item: CollectionItem;
  onOpen(ref: CollectionRef): void;
}) {
  if (item.collection) {
    return (
      <button
        type="button"
        className={styles.collectionItemButton}
        onClick={() => onOpen(item.collection as CollectionRef)}
        title={`Open ${item.name}`}
      >
        <ConceptGlyph concept={item.concept} className={styles.collectionItemMark} />
        <span>{item.name}</span>
      </button>
    );
  }
  return (
    <ConceptPill
      concept={item.concept}
      name={item.name}
      component={item.component}
      property={item.property}
      ownerConcept={item.ownerConcept}
      bindingIndex={item.bindingIndex}
      stepId={item.stepId}
    />
  );
}

export function CollectionEditor(props: WorkspaceProps) {
  const selection = documentSelection(activeDocument(props.state));
  const id = selection?.collection ?? "assets";
  const component = selection?.component;
  const model = useMemo(
    () => collectionModel(props.state.index, id, component),
    [props.state.index, id, component],
  );
  const constitution = useMemo(
    () => collectionDagModel(model, "dependency"),
    [model],
  );
  const contribution = useMemo(
    () => collectionDagModel(model, "contribution"),
    [model],
  );

  const open = (ref: CollectionRef) => openCollection(props, ref);
  const itemRows: MemberRow[] = model.items.rows.map((item) => ({
    key: item.key,
    title: item.name,
    cells: [<ItemLabel key="label" item={item} onOpen={open} />, ...item.cells],
  }));

  return (
    <DetailDocument
      testId="collection-editor"
      concept={model.concept}
      kicker={model.kicker}
      title={model.title}
      subtitle={model.subtitle}
      facts={model.facts}
    >
      <DetailBand
        concept={model.concept}
        title="Constitution"
        question="How does this collection come to be?"
        testId="collection-constitution"
      >
        <Constitution model={constitution} />
      </DetailBand>

      <DetailBand
        concept="graph"
        title="Contribution"
        question="Which layer depends on this collection?"
        testId="collection-contribution"
      >
        <Constitution model={contribution} label="Contribution" />
      </DetailBand>

      <DetailBand
        concept={model.concept}
        title="Items"
        question="Which participants belong to this collection?"
        testId="collection-items"
      >
        <MemberTable
          columns={model.items.columns}
          template={model.items.template}
          rows={itemRows}
          empty={model.items.empty}
        />
      </DetailBand>

      <DetailBand
        concept="semantics"
        title="Coverage"
        question="How complete is this collection?"
        testId="collection-coverage"
      >
        <ul className={styles.coverageList}>
          {model.coverage.map((row) => (
            <li key={row.key} className={styles.coverageItem}>
              <span className={styles.coverageMeasure}>{row.measure}</span>
              <span className={styles.coverageCount}>{row.count}</span>
              <span className={styles.coverageReading}>{row.reading}</span>
            </li>
          ))}
        </ul>
      </DetailBand>
    </DetailDocument>
  );
}
