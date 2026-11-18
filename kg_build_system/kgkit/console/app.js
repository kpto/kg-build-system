(() => {
  "use strict";

  const TABS = [
    { id: "viewer", label: "Viewer", icon: "eye", group: "Read" },
    { id: "iteration", label: "Iteration", icon: "loop", group: "Loop" },
    { id: "revisions", label: "Revisions", icon: "graph", kind: "revision", group: "Loop" },
    { id: "evaluations", label: "Evaluations", icon: "play", kind: "evaluation", group: "Evaluate" },
    { id: "findings", label: "Findings", icon: "check", kind: "finding", group: "Change" },
    { id: "designs", label: "Designs", icon: "doc", kind: "change_design", group: "Change" },
  ];

  const ICONS = {
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    review: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    loop: '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6h6a4 4 0 0 1 4 4v6"/>',
    graph: '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="7" r="2"/><circle cx="12" cy="18" r="2"/><path d="m8 6 8 1M7.5 8l4 8M16.7 9l-3.7 7"/>',
    design: '<path d="M5 3h14v18H5z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    play: '<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4z"/>',
    chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    bulb: '<path d="M12 3a6 6 0 0 0-3.5 10.9c.6.4 1 1 1 1.7V18h5v-2.4c0-.7.4-1.3 1-1.7A6 6 0 0 0 12 3Z"/><path d="M10 21h4"/>',
    doc: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6"/>',
  };
  const KIND_TAB = {
    revision: "revisions",
    evaluation: "evaluations",
    finding: "findings",
    change_design: "designs",
  };

  const app = document.getElementById("app");
  const previewEl = document.getElementById("preview");
  const state = {
    objects: [],
    timeline: [],
    views: [],
    active: "viewer",
    viewerUrl: "http://127.0.0.1:3000/?embed=1",
    project: "",
    viewerMode: "reviewer",
    revisionId: null,
    subject: null,
    history: [{ tab: "viewer" }],
    historyIndex: 0,
    scrollPositions: {},
    preview: null,
    timer: null,
  };

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[char]);
  const icon = (name) => `<svg class="kg-rail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
  const slug = (id) => "object-" + String(id).replace(/[^a-zA-Z0-9_-]/g, "_");
  const short = (id) => String(id || "").replace(/^KG-/, "").slice(0, 12);
  const objectsOf = (kind) => state.objects.filter((object) => object.kind === kind);
  const createdAt = (object) => {
    const parsed = Date.parse(object.created || "");
    return Number.isNaN(parsed) ? 0 : parsed;
  };
  const recentFirst = (objects) =>
    objects.slice().sort((left, right) => {
      const byTime = createdAt(right) - createdAt(left);
      return byTime || String(right.id).localeCompare(String(left.id));
    });
  const objectById = (id) => state.objects.find((object) => object.id === id);
  const tabFor = (id) => TABS.find((tab) => tab.id === id) || TABS[0];
  const time = (value) => {
    const date = new Date(value || "");
    return Number.isNaN(date.getTime()) ? String(value || "") : date.toLocaleString();
  };
  const chip = (text, tone) => `<span class="kg-chip kg-chip-${esc(tone || "neutral")}">${esc(text)}</span>`;

  function fieldHtml(field) {
    const value = esc(field.value);
    if (field.kind === "pill") return chip(field.value, field.tone);
    if (field.kind === "code") return `<code>${value}</code>`;
    if (field.kind === "metric") return `<span class="kg-event-metric">${value}</span>`;
    if (field.kind === "link") {
      return /^https?:/i.test(field.value)
        ? `<a class="kg-link" href="${esc(field.value)}" target="_blank" rel="noreferrer">${value}</a>`
        : `<code>${value}</code>`;
    }
    return value;
  }

  function linkChip(id, kind, role) {
    if (!id) return "";
    return `<button type="button" class="kg-event-ref" data-preview-id="${esc(id)}" data-preview-kind="${esc(kind)}" title="Preview ${esc(id)}">${role ? `${esc(role)} · ` : ""}${esc(id)}</button>`;
  }

  function timelineLinks(row) {
    const refs = Array.isArray(row.refs) && row.refs.length
      ? row.refs
      : row.entity_id ? [{ id: row.entity_id, kind: row.entity_kind || "" }] : [];
    return refs.map((ref) => linkChip(ref.id, ref.kind, "")).join("");
  }

  function objectCard(object) {
    const fields = (object.fields || []).map((field) => `<dt>${esc(field.label)}</dt><dd>${fieldHtml(field)}</dd>`).join("");
    const links = (object.links || []).map((link) => linkChip(link.id, link.kind, link.role)).join("");
    const events = state.timeline.filter((row) => row.entity_id === object.id || (row.refs || []).some((ref) => ref.id === object.id)).slice().reverse();
    const backlinks = events.map((row) => `<button type="button" class="kg-event-ref" data-event-id="${esc(row.id)}">${esc(row.id)}</button>`).join("");
    return `<article class="kg-object" id="${slug(object.id)}" data-object-id="${esc(object.id)}">
      <div class="kg-object-head">${chip(object.kind || "object", "info")}<code class="kg-object-id">${esc(object.id)}</code></div>
      <h3 class="kg-object-title">${esc(object.kind === "revision" ? object.message || object.title || object.id : object.title || object.id)}</h3>
      ${object.kind !== "revision" && object.summary ? `<p class="kg-object-summary">${esc(object.summary)}</p>` : ""}
      ${fields ? `<dl class="kg-event-fields">${fields}</dl>` : ""}
      ${links ? `<div class="kg-object-links"><span class="kg-label">Links</span>${links}</div>` : ""}
      ${object.kind === "revision" && object.view_file ? `<button type="button" class="kg-object-view" data-view-revision="${esc(object.id)}">View revision</button>` : ""}
      <div class="kg-object-meta"><span class="kg-label">Created</span><time datetime="${esc(object.created || "")}" title="${esc(object.created || "")}">${esc(time(object.created))}</time><span class="kg-sep">·</span><span class="kg-label">Source</span><code>${esc(object.source || "")}</code></div>
      <div class="kg-object-events"><span class="kg-label">Timeline</span>${backlinks || '<span class="kg-event-root">none</span>'}</div>
    </article>`;
  }

  function renderObjects(tab) {
    const objects = recentFirst(objectsOf(tab.kind));
    return `<section class="kg-objects"><div class="kg-section-head"><span class="kg-label">${esc(tab.label)}</span><span class="kg-count">${objects.length}</span></div>${objects.length ? objects.map(objectCard).join("") : '<p class="kg-empty">No rows.</p>'}</section>`;
  }

  const TIMELINE_METRICS = {
    cardWidth: 264,
    cardHeight: 220,
    laneWidth: 184,
    rowGap: 30,
    padding: 12,
  };
  const LANE_PALETTE = ["var(--kg-lane-0)", "var(--kg-lane-1)", "var(--kg-lane-2)", "var(--kg-lane-3)"];
  const laneColor = (lane) => LANE_PALETTE[lane % LANE_PALETTE.length];
  const TYPE_PALETTE = ["revision-added", "evaluation-added", "design-proposed", "design-adopted", "design-superseded", "design-abandoned", "finding-added"];
  const typeColor = (type) => {
    const slug = String(type || "").replaceAll("_", "-");
    return `var(--kg-type-${TYPE_PALETTE.includes(slug) ? slug : "default"})`;
  };
  const typeLabel = (type) => String(type || "event").replaceAll("_", " ");
  const minute = (value) => {
    const date = new Date(value || "");
    if (Number.isNaN(date.getTime())) return String(value || "");
    const pad = (number) => String(number).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  function eventCardHtml(card, { measure = false } = {}) {
    const event = card.event;
    const record = card.record;
    const badges = [
      event.temporary ? chip("temporary", "pending") : "",
      record.parents.length > 1 ? chip("merge", "accepted") : "",
      record.children.length > 1 ? chip(`fork ${record.children.length}`, "pending") : "",
      record.children.length === 0 ? chip("head", "info") : "",
    ].join("");
    const style = measure
      ? `--kg-type:${typeColor(event.type)}; width:${card.width}px`
      : `--kg-type:${typeColor(event.type)}; left:${card.x}px; top:${card.y}px; width:${card.width}px; height:${card.height}px`;
    return `<article class="kg-event-card kg-dag-card${measure ? " kg-dag-measure-card" : ""}" id="${measure ? "" : slug(event.id)}" data-event-id="${esc(event.id)}" data-lane="${card.lane}" style="${style}">
      <div class="kg-dag-cap"><span>${esc(typeLabel(event.type))}</span><time class="kg-dag-time" datetime="${esc(event.timestamp || "")}" title="${esc(time(event.timestamp))}">${esc(minute(event.timestamp))}</time></div>
      <div class="kg-event-head"><code class="kg-event-id">${esc(event.id)}</code>${badges}</div>
      ${event.entity_kind === "revision" && event.message
        ? `<div class="kg-event-commit">${esc(event.message)}</div>`
        : `<h3 class="kg-event-title">${esc(event.title || event.id)}</h3>`}
      ${timelineLinks(event) ? `<div class="kg-event-refs"><span class="kg-label">Links</span>${timelineLinks(event)}</div>` : ""}
    </article>`;
  }

  function measureEventCards(cards) {
    const host = document.createElement("div");
    host.className = "kg-dag-measure";
    host.style.width = `${TIMELINE_METRICS.cardWidth}px`;
    document.body.appendChild(host);
    const heights = {};
    for (const card of cards) {
      host.innerHTML = eventCardHtml(card, { measure: true });
      const element = host.firstElementChild;
      heights[card.id] = Math.ceil(element.getBoundingClientRect().height);
    }
    host.remove();
    return heights;
  }

  function renderTimeline() {
    const provisional = KGIterationGraph.layout(state.timeline, TIMELINE_METRICS);
    const cardHeights = measureEventCards(provisional.cards);
    const graph = KGIterationGraph.layout(state.timeline, { ...TIMELINE_METRICS, cardHeights });
    const { width, height, gaps } = graph;
    const edges = graph.edges.map((edge) =>
      `<path d="${edge.d}" stroke="${laneColor(edge.lane)}" data-child="${esc(edge.child)}" data-parent="${esc(edge.parent)}" />`,
    );
    const cards = graph.cards.map((card) => eventCardHtml(card)).join("");
    const rules = gaps
      .map((gap) => `<span style="top:${(gap.top + gap.bottom) / 2}px"></span>`)
      .join("");
    return `<section class="kg-iteration"><div class="kg-section-head"><span class="kg-label">Iteration graph</span><div class="kg-section-actions"><button type="button" class="kg-section-refresh" data-action="reload">Refresh</button></div></div>${graph.cards.length ? `<div class="kg-dag-scroll"><div class="kg-dag" style="height:${height}px"><div class="kg-dag-rules" aria-hidden="true">${rules}</div><div class="kg-dag-canvas" style="width:${width}px; height:${height}px"><svg class="kg-dag-edges" width="${width}" height="${height}" aria-hidden="true">${edges.join("")}</svg>${cards}</div></div></div>` : '<p class="kg-empty">No rows in the iteration timeline.</p>'}</section>`;
  }

  function resolvedViewerUrl() {
    try {
      const url = new URL(state.viewerUrl, window.location.href);
      // A loopback viewer URL only works when the console is opened on the
      // same machine. Rewrite it to the host the console was served from so
      // the embedded iframe reaches the viewer over the same network path.
      if (["127.0.0.1", "localhost", "0.0.0.0", "[::1]", "::1"].includes(url.hostname)) {
        url.hostname = window.location.hostname;
      }
      url.searchParams.set("embed", "1");
      return url;
    } catch {
      return null;
    }
  }

  function viewerSrc() {
    const resolved = resolvedViewerUrl();
    return resolved ? resolved.toString() : state.viewerUrl;
  }

  function viewerOrigin() {
    const resolved = resolvedViewerUrl();
    return resolved ? resolved.origin : "*";
  }

  async function postView(frame) {
    const url = state.revisionId
      ? `/api/revision-view?revision=${encodeURIComponent(state.revisionId)}`
      : "/api/current-view";
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) throw new Error(`revision view request failed: ${response.status}`);
      const view = await response.json();
      frame.contentWindow?.postMessage(
        { type: "open", snapshot: view, label: state.revisionId || "current" },
        viewerOrigin(),
      );
    } catch (cause) {
      state.subject = null;
      updateSubject();
      console.warn("Could not open the revision view:", cause);
    }
  }

  function revisionObjects() {
    return recentFirst(objectsOf("revision"));
  }

  function selectRevision(id) {
    const next = id || null;
    if (state.revisionId === next) return;
    state.revisionId = next;
    state.subject = null;
    document.querySelectorAll(".kg-revision-item").forEach((item) => {
      const button = item.querySelector("[data-revision-id]");
      const selected = (button?.dataset.revisionId || null) === next;
      item.classList.toggle("kg-revision-item-selected", selected);
      button?.setAttribute("aria-selected", selected ? "true" : "false");
    });
    const frame = document.getElementById("viewer-frame");
    if (frame) postView(frame);
  }

  function renderRevisionTimeline() {
    const revisions = revisionObjects();
    const current = (state.views || []).find((view) => view.kind === "current");
    const currentItem = `<div class="kg-revision-item${state.revisionId ? "" : " kg-revision-item-selected"}">
      <button type="button" role="tab" class="kg-revision-main" data-revision-id="" aria-selected="${state.revisionId ? "false" : "true"}" title="Show the latest compilation">
        <span class="kg-revision-time">latest</span>
        <span class="kg-revision-title">Current compilation</span>
        <span class="kg-revision-meta">${current?.file ? "snapshot present" : "no snapshot yet"}</span>
        <span class="kg-revision-id">current</span>
      </button>
    </div>`;
    const items = revisions.map((object) => {
      const selected = state.revisionId === object.id;
      const hasView = Boolean(object.view_file);
      const fields = Object.fromEntries((object.fields || []).map((field) => [field.label, field.value]));
      const meta = [
        fields["Nodes"] && fields["Edges"] ? `${fields["Nodes"]} / ${fields["Edges"]}` : "",
        fields["Manifest"] || "",
        fields["Suites Passed"] && fields["Suites Total"] ? `${fields["Suites Passed"]}/${fields["Suites Total"]} suites` : "",
      ].filter(Boolean).join(" · ");
      return `<div class="kg-revision-item${selected ? " kg-revision-item-selected" : ""}">
        <button type="button" role="tab" class="kg-revision-main" data-revision-id="${esc(object.id)}" aria-selected="${selected ? "true" : "false"}" ${hasView ? "" : "disabled"} title="${hasView ? "Open this revision" : "No captured view for this revision"}">
          <span class="kg-revision-time">${esc(time(object.created))}</span>
          <span class="kg-revision-title">${esc(object.title || object.id)}</span>
          <span class="kg-revision-meta">${esc(meta)}</span>
          <span class="kg-revision-id">${esc(object.id)}</span>
        </button>
        <button type="button" class="kg-revision-event" data-event-id="${esc(object.event_id || object.id)}" title="Show this revision event in Iteration">event</button>
      </div>`;
    }).join("");
    return `<div class="kg-revision-timeline" role="tablist" aria-label="Graph revisions">
      ${currentItem}
      ${items}
      ${revisions.length ? "" : '<p class="kg-revision-empty">No revisions yet. A revision closes a resolved design set.</p>'}
    </div>`;
  }

  function renderViewer() {
    const url = viewerSrc();
    const controls = state.viewerMode === "timeline"
      ? renderRevisionTimeline()
      : `<div class="kg-subject ${state.subject ? "" : "kg-subject-empty"}"><span class="kg-label">Subject</span><code id="subject">${esc(state.subject || "none selected")}</code>${state.revisionId ? '<span class="kg-mode-note">revision view</span>' : ""}</div>
        <div class="kg-actions">
        </div>`;
    return `<div class="kg-viewer">
      <div class="kg-viewer-tools">
        <button type="button" class="kg-mode-switch" data-viewer-mode="${state.viewerMode === "reviewer" ? "timeline" : "reviewer"}" aria-label="${state.viewerMode === "reviewer" ? "Switch to Timeline" : "Switch to Reviewer"}" title="${state.viewerMode === "reviewer" ? "Switch to Timeline" : "Switch to Reviewer"}" aria-pressed="${state.viewerMode === "timeline" ? "true" : "false"}">
          <span class="kg-mode-option" data-active="${state.viewerMode === "reviewer" ? "true" : "false"}">${icon("review")}</span>
          <span class="kg-mode-option" data-active="${state.viewerMode === "timeline" ? "true" : "false"}">${icon("clock")}</span>
        </button>
        <div class="kg-viewer-tool-main">${controls}</div>
      </div>
      <div class="kg-frame-wrap"><iframe id="viewer-frame" class="kg-frame" title="Knowledge graph viewer" src="${esc(url)}" referrerpolicy="no-referrer"></iframe></div>
      <div id="subject-panel" class="kg-subject-panel" hidden></div>
    </div>`;
  }

  function renderRail() {
    let html = "";
    let group = "";
    for (const tab of TABS) {
      if (tab.group !== group) {
        if (group) html += "</div>";
        html += `<div class="kg-rail-group"><span class="kg-rail-group-label">${esc(tab.group)}</span>`;
        group = tab.group;
      }
      const count = tab.id === "iteration" ? state.timeline.length : tab.kind ? objectsOf(tab.kind).length : 0;
      html += `<button type="button" class="kg-rail-button" data-tab="${tab.id}" aria-selected="${state.active === tab.id ? "true" : "false"}" title="${esc(tab.label)}">${icon(tab.icon)}<span class="kg-rail-label">${esc(tab.label)}</span>${count ? `<span class="kg-rail-count">${count}</span>` : ""}</button>`;
    }
    if (group) html += "</div>";
    return `<nav class="kg-rail" aria-label="Relation tabs">${html}</nav>`;
  }

  function renderHeader() {
    const revision = recentFirst(objectsOf("revision"))[0];
    const fields = Object.fromEntries((revision?.fields || []).map((field) => [field.label, field.value]));
    return `<header class="kg-header"><div class="kg-title-row"><div class="kg-title-left"><span class="kg-kicker">${esc(state.project || "KG")} / RELATIONS</span><div class="kg-history"><button type="button" class="kg-history-button" data-action="back" aria-label="Back" title="Back (mouse button 3)" ${state.historyIndex === 0 ? "disabled" : ""}>←</button><button type="button" class="kg-history-button" data-action="forward" aria-label="Forward" title="Forward (mouse button 4)" ${state.historyIndex >= state.history.length - 1 ? "disabled" : ""}>→</button></div></div><span class="kg-revision">rev ${esc(short(revision?.id))}</span></div><div class="kg-meta"><span class="kg-dot"></span><span>${esc(revision?.title || "revision not loaded")}</span><span class="kg-sep">·</span><span>${fields["Nodes"] || "nodes not reported"} nodes / ${fields["Edges"] || "edges not reported"} edges</span></div></header>`;
  }

  function render() {
    const tab = tabFor(state.active);
    const content = tab.id === "viewer" ? renderViewer() : tab.id === "iteration" ? renderTimeline() : renderObjects(tab);
    app.innerHTML = `<div class="kg-main">${renderHeader()}<div class="kg-content">${content}</div></div>${renderRail()}`;
    bindViewer();
    bindLinks();
  }

  function saveScroll() {
    const content = document.querySelector(".kg-content");
    if (content) state.scrollPositions[state.active] = content.scrollTop;
  }

  function applyEntry(entry) {
    state.active = entry.tab;
    window.history.replaceState(null, "", `#${entry.tab}`);
    render();
    requestAnimationFrame(() => {
      const content = document.querySelector(".kg-content");
      if (!content) return;
      if (entry.target?.type === "object" || entry.target?.type === "event") {
        const node = document.getElementById(slug(entry.target.id));
        node?.scrollIntoView({ block: "center", behavior: "smooth" });
        node?.classList.add(entry.target.type === "event" ? "kg-event-flash" : "kg-object-flash");
        setTimeout(() => node?.classList.remove("kg-event-flash", "kg-object-flash"), 1400);
      } else {
        content.scrollTop = state.scrollPositions[entry.tab] || 0;
      }
    });
  }

  function navigate(tab, target) {
    if (!TABS.some((item) => item.id === tab)) tab = "viewer";
    if (tab === state.active && !target) return;
    saveScroll();
    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push({ tab, target });
    state.historyIndex = state.history.length - 1;
    hidePreview();
    applyEntry(state.history[state.historyIndex]);
  }

  function setTab(id) {
    navigate(id);
  }

  function goBack() {
    if (state.historyIndex === 0) return;
    saveScroll();
    state.historyIndex -= 1;
    hidePreview();
    applyEntry(state.history[state.historyIndex]);
  }

  function goForward() {
    if (state.historyIndex >= state.history.length - 1) return;
    saveScroll();
    state.historyIndex += 1;
    hidePreview();
    applyEntry(state.history[state.historyIndex]);
  }

  function embedSubjectKey(value) {
    if (typeof value === "string" && value.trim()) return value.trim();
    if (!value || typeof value !== "object") return null;
    const kind = String(value.kind || "").trim();
    const name = String(value.name || "").trim();
    if (!kind || !name) return null;
    if (kind === "property") {
      const component = String(value.component || "").trim();
      const property = String(value.property || name).trim();
      return component ? `property:${component}.${property}` : `property:${property}`;
    }
    return `${kind}:${name}`;
  }

  function updateSubject() {
    const node = document.getElementById("subject");
    if (!node) return;
    node.textContent = state.subject || "none selected";
    node.parentElement?.classList.toggle("kg-subject-empty", !state.subject);
  }

  function bindSubjectPanel() {
    document.querySelector("[data-close-subject]")?.addEventListener("click", () => {
      const panel = document.getElementById("subject-panel");
      if (panel) { panel.hidden = true; panel.innerHTML = ""; }
    });
  }

  async function fetchGraphSubject(key) {
    try {
      const response = await fetch(`/api/graph-subject?key=${encodeURIComponent(key)}`, { cache: "no-store" });
      if (!response.ok) return null;
      return await response.json();
    } catch {
      return null;
    }
  }

  function renderGraphSubject(data) {
    const node = data.node;
    if (node) {
      const label = node.label || node.name || node.build_key;
      const props = Object.entries(node)
        .filter(([name]) => !["kind", "_kg_binding_symbol", "source", "evidence"].includes(name))
        .slice(0, 14)
        .map(([name, value]) => `<dt>${esc(name)}</dt><dd>${esc(typeof value === "object" ? JSON.stringify(value) : value)}</dd>`)
        .join("");
      const edges = (data.edges || []).slice(0, 40).map((edge) => {
        const evidence = (edge.evidence || []).map((row) => `<li><code>${esc(row.type || row.source || "evidence")}</code>${row.evidence ? ` · ${esc(row.evidence)}` : ""}${row.score !== null && row.score !== undefined ? ` · score ${esc(row.score)}` : ""}</li>`).join("");
        return `<li class="kg-subject-edge"><span class="kg-chip">${esc(edge.type)}</span> <code>${esc(edge.source)}</code> → <code>${esc(edge.target)}</code><div class="kg-explanation-row">${esc(edge.source_label || "")} → ${esc(edge.target_label || "")} · evidence ${esc(edge.evidence_total)}</div>${evidence ? `<ul class="kg-explanation-list">${evidence}</ul>` : ""}</li>`;
      }).join("");
      return `<article class="kg-explanation"><div class="kg-explanation-head"><span class="kg-label">${esc(node.type || "node")}</span><code>${esc(node.build_key)}</code><button type="button" class="kg-button" data-close-subject>Close</button></div><h3 class="kg-subject-title">${esc(label)}</h3><dl class="kg-subject-props">${props}</dl>${edges ? `<div class="kg-explanation-block"><span class="kg-label">Relations · ${(data.edges || []).length}</span><ul class="kg-explanation-list">${edges}</ul></div>` : '<p class="kg-empty">No relations.</p>'}</article>`;
    }
    const edge = data.edge;
    if (edge) {
      const evidence = (edge.evidence || []).slice(0, 8).map((row) => `<li><code>${esc(row.type || row.source || "evidence")}</code>${row.evidence ? ` · ${esc(row.evidence)}` : ""}${row.score !== null && row.score !== undefined ? ` · score ${esc(row.score)}` : ""}</li>`).join("");
      return `<article class="kg-explanation"><div class="kg-explanation-head"><span class="kg-label">${esc(edge.type || "edge")}</span><code>${esc(edge.build_key)}</code><button type="button" class="kg-button" data-close-subject>Close</button></div><p class="kg-explanation-purpose"><code>${esc(edge.source)}</code> → <code>${esc(edge.target)}</code></p><p class="kg-explanation-row">${esc(edge.source_label || "")} → ${esc(edge.target_label || "")} · evidence ${esc(edge.evidence_total)}${edge.source_file ? ` · ${esc(edge.source_file)}` : ""}</p>${evidence ? `<div class="kg-explanation-block"><span class="kg-label">Evidence rows</span><ul class="kg-explanation-list">${evidence}</ul></div>` : ""}</article>`;
    }
    return "";
  }

  async function openSubject(key) {
    const panel = document.getElementById("subject-panel");
    if (!panel) return;
    const text = String(key || "").trim();
    if (!text) return;
    try {
      const graph = await fetchGraphSubject(text);
      if (graph && graph.ok) {
        state.subject = graph.node?.build_key || graph.edge?.build_key || text;
        updateSubject();
        panel.hidden = false;
        panel.innerHTML = renderGraphSubject(graph);
        bindSubjectPanel();
        return;
      }
      panel.hidden = true;
      panel.innerHTML = "";
    } catch (cause) {
      panel.hidden = false;
      panel.innerHTML = `<p class="kg-empty">Could not load subject: ${esc(String(cause))}</p>`;
    }
  }

  function bindViewer() {
    document.querySelectorAll("[data-viewer-mode]").forEach((button) => {
      button.addEventListener("click", () => {
        state.viewerMode = button.dataset.viewerMode;
        render();
      });
    });
    document.querySelectorAll("[data-revision-id]").forEach((button) => {
      button.addEventListener("click", () => selectRevision(button.dataset.revisionId || ""));
    });
  }

  window.addEventListener("message", (event) => {
    const frame = document.getElementById("viewer-frame");
    if (!frame || event.source !== frame.contentWindow) return;
    const origin = viewerOrigin();
    if (origin !== "*" && event.origin !== origin) return;
    const data = event.data;
    if (!data || typeof data !== "object") return;
    if (data.type === "ready") {
      postView(frame);
      return;
    }
    if (data.type === "error") {
      state.subject = null;
      updateSubject();
      return;
    }
    const subject = embedSubjectKey(data.subject);
    if (!subject) return;
    state.subject = subject;
    updateSubject();
    openSubject(subject);
  });

  function bindLinks() {
    document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => setTab(button.dataset.tab)));
    // Only the id buttons jump between events; the card itself carries
    // data-event-id for tooling, and clicking it must not re-render the view.
    document.querySelectorAll("button[data-event-id]").forEach((button) => button.addEventListener("click", () => navigate("iteration", { type: "event", id: button.dataset.eventId })));
    document.querySelectorAll("[data-view-revision]").forEach((button) => button.addEventListener("click", () => openObject(button.dataset.viewRevision, "revision")));
    document.querySelector("[data-action='reload']")?.addEventListener("click", load);
    document.querySelector("[data-action='back']")?.addEventListener("click", goBack);
    document.querySelector("[data-action='forward']")?.addEventListener("click", goForward);
  }

  function openObject(id, kind) {
    hidePreview();
    if (kind === "revision") {
      const object = objectById(id);
      if (object?.view_file) {
        state.revisionId = id;
        state.viewerMode = "timeline";
        if (state.active === "viewer") render();
        else navigate("viewer");
      } else {
        navigate("revisions", { type: "object", id });
      }
      return;
    }
    navigate(KIND_TAB[kind] || "findings", { type: "object", id });
  }

  function showPreview(id, kind, element) {
    clearTimeout(state.timer);
    state.preview = { id, kind, rect: element.getBoundingClientRect() };
    renderPreview();
  }

  function scheduleHide() {
    clearTimeout(state.timer);
    state.timer = setTimeout(() => hidePreview(), 80);
  }

  function hidePreview() {
    state.preview = null;
    previewEl.hidden = true;
    previewEl.innerHTML = "";
  }

  function renderPreview() {
    if (!state.preview) { hidePreview(); return; }
    const object = objectById(state.preview.id);
    if (!object) { hidePreview(); return; }
    const fields = (object.fields || []).map((field) => `<dt>${esc(field.label)}</dt><dd>${fieldHtml(field)}</dd>`).join("");
    previewEl.innerHTML = `<div class="kg-preview-head">${chip(object.kind || "object", "info")}<code class="kg-preview-id">${esc(object.id)}</code></div><h3 class="kg-preview-title">${esc(object.title || object.id)}</h3>${object.summary ? `<p class="kg-object-summary">${esc(object.summary)}</p>` : ""}${fields ? `<dl class="kg-event-fields">${fields}</dl>` : ""}`;
    const width = Math.min(320, window.innerWidth - 16);
    const rect = state.preview.rect;
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    const above = rect.bottom > window.innerHeight * 0.62;
    previewEl.style.left = `${left}px`;
    previewEl.style.width = `${width}px`;
    previewEl.style.top = above ? "auto" : `${rect.bottom + 6}px`;
    previewEl.style.bottom = above ? `${window.innerHeight - rect.top + 6}px` : "auto";
    previewEl.hidden = false;
  }

  document.addEventListener("mouseover", (event) => {
    const chip = event.target.closest("[data-preview-id]");
    if (chip) showPreview(chip.dataset.previewId, chip.dataset.previewKind, chip);
  });
  document.addEventListener("mouseout", (event) => {
    const chip = event.target.closest("[data-preview-id]");
    if (!chip) return;
    const next = event.relatedTarget;
    if (next && (previewEl.contains(next) || next.closest?.("[data-preview-id]"))) return;
    scheduleHide();
  });
  document.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-preview-id]");
    if (chip) {
      event.preventDefault();
      openObject(chip.dataset.previewId, chip.dataset.previewKind);
    }
  });
  previewEl.addEventListener("mouseenter", () => clearTimeout(state.timer));
  previewEl.addEventListener("mouseleave", scheduleHide);
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") hidePreview(); });
  window.addEventListener("hashchange", () => {
    const id = location.hash.slice(1);
    if (TABS.some((tab) => tab.id === id) && id !== state.active) {
      state.active = id;
      state.history = state.history.slice(0, state.historyIndex + 1);
      state.history.push({ tab: id });
      state.historyIndex = state.history.length - 1;
      render();
    }
  });
  window.addEventListener("mousedown", (event) => {
    if (event.button === 3) { event.preventDefault(); goBack(); }
    else if (event.button === 4) { event.preventDefault(); goForward(); }
  });

  async function load() {
    try {
      const [relationsResponse, configResponse] = await Promise.all([
        fetch("api/relations", { cache: "no-store" }),
        fetch("api/config", { cache: "no-store" }),
      ]);
      const relations = await relationsResponse.json();
      state.objects = relations.objects || [];
      state.timeline = relations.timeline || [];
      state.views = relations.views || [];
      const config = await configResponse.json();
      if (config.viewerUrl) state.viewerUrl = config.viewerUrl;
      if (config.project) {
        state.project = String(config.project);
        document.title = `${state.project} · KG console`;
      }
      render();
    } catch (cause) {
      app.innerHTML = `<div class="kg-loading">Could not load the relation catalog: ${esc(cause.message)}</div>`;
    }
  }

  const initial = location.hash.slice(1);
  if (TABS.some((tab) => tab.id === initial)) state.active = initial;
  state.history = [{ tab: state.active }];
  state.historyIndex = 0;
  load();
})();
