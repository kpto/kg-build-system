import { describe, expect, it } from "vitest";

import {
  activeFinding,
  auditReportFor,
  countBySubject,
  decisionForFinding,
  defaultAuditFilters,
  filterAuditFindings,
  findingSubjectKind,
  proofSelectionFor,
  subjectLabel,
} from "@/audit/auditData";
import { buildAudit, auditRuleGroup } from "@/lib/audit";
import type { ReviewSidecar } from "@/lib/reviewTypes";
import { contractIndex } from "./fixtures";

const report = buildAudit(contractIndex);

describe("audit view model", () => {
  it("shares one deterministic report per index", () => {
    expect(auditReportFor(contractIndex)).toBe(auditReportFor(contractIndex));
    expect(auditReportFor(contractIndex)).toEqual(report);
  });

  it("defaults the audit queue to the Identity group", () => {
    const filters = defaultAuditFilters();
    expect(filters.group).toBe("identity");

    const visible = filterAuditFindings(report.findings, filters);
    expect(visible.length).toBeGreaterThan(0);
    expect(visible.length).toBeLessThan(report.findings.length);
    expect(visible.every((finding) => auditRuleGroup(finding.rule) === "identity")).toBe(
      true,
    );
  });

  it("filters by severity, rule, subject kind and query", () => {
    const filters = { ...defaultAuditFilters(), group: null };
    expect(filterAuditFindings(report.findings, filters)).toHaveLength(
      report.findings.length,
    );

    const high = filters.severities.filter((severity) => severity !== "high");
    expect(
      filterAuditFindings(report.findings, { ...filters, severities: high }),
    ).toHaveLength(report.findings.filter((finding) => finding.severity !== "high").length);

    const first = report.findings[0];
    expect(
      filterAuditFindings(report.findings, { ...filters, rule: first.rule }),
    ).toEqual(report.findings.filter((finding) => finding.rule === first.rule));

    const kind = findingSubjectKind(first);
    expect(
      filterAuditFindings(report.findings, { ...filters, subjectKind: kind }).every(
        (finding) => findingSubjectKind(finding) === kind,
      ),
    ).toBe(true);

    const needle = first.subject?.name?.slice(0, 3) ?? first.rule;
    expect(
      filterAuditFindings(report.findings, { ...filters, query: needle }).length,
    ).toBeGreaterThan(0);
  });

  it("keeps a hidden selection and otherwise falls back to the first visible finding", () => {
    const first = report.findings[0];
    expect(activeFinding(report, report.findings, first.id)).toBe(first);

    const hidden = report.findings.find((finding) => finding.id !== first.id);
    if (hidden) {
      expect(
        activeFinding(report, [first], hidden.id),
      ).toBe(hidden);
    }
    expect(activeFinding(report, [first], undefined)).toBe(first);
    expect(activeFinding(report, [], undefined)).toBeUndefined();
  });

  it("finds the sidecar decision attached to a finding subject", () => {
    const finding = report.findings.find((entry) => entry.subject);
    if (!finding?.subject) throw new Error("fixture has no subject finding");
    const review: ReviewSidecar = {
      format: "kg-viewer-review",
      version: 1,
      decisions: [
        {
          id: "decision-1",
          title: "Accept the fixture subject",
          status: "accepted",
          rationale: "Fixture decision.",
          evidence: finding.evidence,
          subject: finding.subject,
        },
      ],
    };
    expect(decisionForFinding(review, finding)?.id).toBe("decision-1");
    expect(decisionForFinding({ ...review, decisions: [] }, finding)).toBeUndefined();
  });

  it("maps a subject finding to a proof selection without inventing a target", () => {
    const property = report.findings.find(
      (finding) => finding.subject?.kind === "property",
    );
    if (property) {
      const selection = proofSelectionFor(property);
      expect(selection).toMatchObject({
        activity: "proof",
        kind: "property",
        component: property.subject?.component,
        property: property.subject?.property,
        level: "property",
      });
    }

    const graph = report.findings.find(
      (finding) => finding.subject?.kind === ("graph" as never),
    );
    if (graph) expect(proofSelectionFor(graph)).toBeNull();
  });

  it("groups rules and labels subjects deterministically", () => {
    expect(auditRuleGroup("identity.nullable-key")).toBe("identity");
    expect(auditRuleGroup("coverage.unbound-property")).toBe("coverage");
    expect(auditRuleGroup("semantics.missing")).toBe("semantics");
    expect(auditRuleGroup("type.shape-mismatch")).toBe("type");
    expect(auditRuleGroup("graph.purpose-missing")).toBe("graph");

    for (const finding of report.findings) {
      expect(subjectLabel(finding).length).toBeGreaterThan(0);
      expect(findingSubjectKind(finding).length).toBeGreaterThan(0);
    }
    const subjects = countBySubject(report.findings);
    expect(subjects.reduce((total, entry) => total + entry.count, 0)).toBe(
      report.findings.length,
    );
  });
});
