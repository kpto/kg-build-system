"""Self-contained HTML rendering for the meta graph document.

The generated page inlines d3 and embeds the same JSON the module writes beside
it, so a single file can be archived, emailed, or opened from a CI artifact with
no network and no sibling assets.
"""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

_D3_MARKER = "%%%D3%%%"
_DATA_MARKER = "%%DATA%%"

# Raw because the template's JavaScript carries regex escapes that Python would
# otherwise read as invalid string escapes.
_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meta graph</title>
<style>
:root { color-scheme: light dark; --canvas: #10141a; }
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.5 system-ui, sans-serif; background: var(--canvas); color: #e6e9ef; }
header { padding: 10px 16px; border-bottom: 1px solid #2a3240; display: flex; gap: 18px; align-items: baseline; flex-wrap: wrap; }
header h1 { font-size: 15px; margin: 0; font-weight: 600; }
header .totals { color: #93a0b4; }
main { display: flex; height: calc(100vh - 49px); }
#graph { flex: 1 1 auto; min-width: 0; position: relative; }
svg { width: 100%; height: 100%; display: block; }
aside { width: 430px; flex: 0 0 430px; border-left: 1px solid #2a3240; padding: 16px 18px 40px; overflow: auto; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; color: #93a0b4; font-size: 12px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.key { width: 13px; height: 13px; border-radius: 50%; display: inline-block; }
.key.concrete { background: #4ea1ff; }
.key.abstract { background: transparent; border: 1.5px dashed #93a0b4; }
.line { width: 22px; border-top: 2px solid #6ee7b7; display: inline-block; }
.line.hierarchy { border-top: 2px dashed #8b93a7; }
.line.category { border-top: 2px dashed #c4a2ff; }
.node { cursor: pointer; }
.node circle { fill: #4ea1ff; stroke: #0b0f14; stroke-width: 1.5px; }
.node.abstract circle { fill: var(--canvas); stroke: #93a0b4; stroke-dasharray: 4 3; }
.node text { fill: #e6e9ef; font-size: 11px; font-weight: 600; cursor: pointer; }
/* Edge names read as annotations on a line rather than as things in the graph:
   monospace, italic and muted, against the upright sans node labels. paint-order
   puts the stroke under the fill, so the halo separates the text from crossing
   lines without thickening the glyphs. Names stay hit-testable and forward to
   their own group, so a label can be pointed at as easily as the line under it. */
.link-label { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 10px;
  font-style: italic; letter-spacing: .03em; fill: #8ea3bf; cursor: pointer;
  paint-order: stroke; stroke: var(--canvas); stroke-width: 3px; stroke-linejoin: round;
  stroke-linecap: round; }
.link-group.dim .link-label { fill: #5d6b7f; }
.node.selected circle, .link-group.selected .link { stroke: #ffd166; stroke-width: 3px; stroke-dasharray: none; stroke-opacity: 1; }
/* What the selection is an instance of, shown in the colour of declarations. */
.node.associated circle, .link-group.associated .link { stroke: #c4a2ff; stroke-width: 2.6px; stroke-dasharray: none; stroke-opacity: 1; }
.node.dim, .link-group.dim { opacity: .18; }
/* Hover is a preview that sits on top of the locked selection, so it must also
   lift an element out of the dimmed background. Declared last for that reason. */
.node.hovered circle, .link-group.hovered .link { stroke: #f8fafc; stroke-width: 3.4px; stroke-dasharray: none; stroke-opacity: 1; }
.node.hovered, .link-group.hovered { opacity: 1; }
.link { stroke: #6ee7b7; stroke-opacity: .8; fill: none; stroke-width: 1.8px; }
.link.hierarchy { stroke: #8b93a7; stroke-dasharray: 5 4; stroke-opacity: .55; }
.link.category { stroke: #c4a2ff; stroke-dasharray: 7 4; stroke-opacity: .85; }
.hit { stroke: transparent; stroke-width: 16px; fill: none; }
.link-group { cursor: pointer; }
/* A hierarchy line is not a component, so it is not interactive. */
.link-group.hierarchy { cursor: default; }
h2 { font-size: 15px; margin: 0 0 4px; }
h3 { font-size: 12px; text-transform: uppercase; letter-spacing: .05em; color: #93a0b4; margin: 20px 0 0; }
.tag { font-size: 11px; padding: 1px 7px; border-radius: 10px; background: #22304a; color: #b9cdf0; margin-left: 6px; vertical-align: 2px; }
.muted, .empty { color: #93a0b4; }
.empty { font-style: italic; }
dl { margin: 12px 0 0; display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; align-items: baseline; }
dt { font-weight: 600; color: #93a0b4; font-size: 12px; }
dd { margin: 0; }
code { font-family: ui-monospace, monospace; font-size: 12px; background: #1a212c; padding: 1px 5px; border-radius: 3px; overflow-wrap: anywhere; }
.property { padding: 12px 0; border-top: 1px solid #232b38; }
.property-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.property-name { font-size: 13px; font-weight: 600; overflow-wrap: anywhere; }
.property-desc { margin: 6px 0 0; color: #c8d0dd; }
.examples { margin: 8px 0 0; }
.examples-label { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #93a0b4; }
.chips { list-style: none; display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 0; padding: 0; }
.chips li { max-width: 100%; }
.chips code { display: block; border-left: 3px solid currentColor; }
.type { font-family: ui-monospace, monospace; font-size: 11px; padding: 1px 7px; border-radius: 4px; border: 1px solid; }
.type.string { color: #7dd3a0; border-color: #2f5b46; background: #152520; }
.type.number { color: #8ab4ff; border-color: #2c3f63; background: #161d2b; }
.type.boolean { color: #dfa6ff; border-color: #4b2c5e; background: #201629; }
.type.array { color: #f0b866; border-color: #5a4321; background: #231c12; }
.type.composite { color: #7fd6e6; border-color: #28505a; background: #122326; }
.nullable { font-size: 11px; color: #93a0b4; border: 1px dashed #3b475a; border-radius: 4px; padding: 1px 6px; }
/* Which category introduced a property, in the violet used for abstractions. */
.inherited { font-size: 11px; font-style: italic; color: #c4a2ff; margin-left: auto; }
.inherit-count { font-weight: 400; text-transform: none; letter-spacing: 0; color: #8ea3bf; }
</style>
</head>
<body>
<header>
  <h1>Meta graph</h1>
  <div class="totals" id="totals"></div>
  <div class="legend">
    <span><i class="key concrete"></i>node component</span>
    <span><i class="key abstract"></i>abstract category</span>
    <span><i class="line"></i>relation</span>
    <span><i class="line category"></i>edge category</span>
    <span><i class="line hierarchy"></i>hierarchy</span>
  </div>
</header>
<main>
  <div id="graph"><svg id="svg" role="img" aria-label="Force-directed diagram of the build topology"></svg></div>
  <aside id="panel"><p class="empty">Select a node or an edge to inspect it.</p></aside>
</main>

<script id="meta-graph-data" type="application/json">%%DATA%%</script>
<script>%%%D3%%%</script>
<script>
/* APP-START */
// Everything below derives strings and data from the meta graph document. None
// of it touches the DOM or d3, so all of it can be exercised outside a browser.

// Length of an arrowhead along the line, in user units. A stroked line stops
// this far short of its target so the head owns the last stretch.
var ARROW_LENGTH = 9;
//
// Edge components are always drawn as links. A concrete one joins the two
// components it targets; an abstract one is a declaration, so it joins the two
// categories it was declared over, which may be abstract and may be the same
// component twice. Declarations get their own colour and dash so the difference
// between "this edge exists" and "edges of this kind relate these kinds" is
// visible without selecting anything.
function buildGraph(data) {
  var vertices = data.nodes.map(describe);
  var drawn = new Set(vertices.map(function (vertex) { return vertex.name; }));
  var links = [];

  data.edges.forEach(function (edge) {
    if (!edge.endpoints) { return; }
    if (!drawn.has(edge.endpoints.source) || !drawn.has(edge.endpoints.target)) { return; }
    links.push({ type: edge.abstract ? 'category' : 'relation',
                 source: edge.endpoints.source, target: edge.endpoints.target,
                 component: edge });
  });

  vertices.forEach(function (vertex) {
    var parent = vertex.component.parent;
    if (parent && drawn.has(parent) && parent !== vertex.name) {
      links.push({ type: 'hierarchy', source: vertex.name, target: parent,
                   component: vertex.component });
    }
  });

  return { nodes: vertices, links: links };

  function describe(component) {
    var rows = component.counts ? component.counts.inclusive_records : 0;
    return {
      name: component.name,
      component: component,
      abstract: !!component.abstract,
      radius: 8 + Math.min(22, Math.sqrt(rows) * 3),
      records: rows
    };
  }
}

function reachable(graph, name) {
  var names = new Set([name]);
  graph.links.forEach(function (link) {
    var source = link.source.name || link.source;
    var target = link.target.name || link.target;
    if (source === name) { names.add(target); }
    if (target === name) { names.add(source); }
  });
  return names;
}

// Colour is keyed on the shape of the type, not its spelling, so a struct and a
// custom scalar read as the same family while strings, numbers, booleans and
// arrays each get their own. Nullability is a separate badge rather than a
// colour, because it is a modifier on every family.
function typeFamily(type) {
  var base = String(type).replace(/\s*\|\s*None\s*$/, '').trim();
  if (base === 'bool') { return 'boolean'; }
  if (base === 'int' || base === 'float') { return 'number'; }
  if (base === 'str') { return 'string'; }
  if (/^Array\s*\[/.test(base)) { return 'array'; }
  return 'composite';
}

// Edges draw straight. Only two things need a bend: a self-declaration, which
// has nowhere to point, and several edges between the same pair of vertices,
// which would otherwise sit exactly on top of one another. Parallel edges get
// symmetric offsets around the straight line.
function spreadLinks(links) {
  var pairs = new Map();
  links.forEach(function (link) {
    link.spread = 0;
    var a = link.source.name || link.source;
    var b = link.target.name || link.target;
    if (a === b) { return; }
    var key = a < b ? a + '|' + b : b + '|' + a;
    var group = pairs.get(key);
    if (!group) { pairs.set(key, group = []); }
    group.push(link);
  });
  pairs.forEach(function (group) {
    if (group.length < 2) { return; }
    group.forEach(function (link, index) {
      link.spread = index - (group.length - 1) / 2;
    });
  });
  return links;
}

// A category declared over a single component has nowhere else to point, so it
// loops back onto itself. The anchors sit either side of the top of the circle
// and each control point lies on the outward radius at its anchor, so the curve
// leaves and returns perpendicular to the surface instead of peeling off at a
// slant.
function loopGeometry(node) {
  var x = node.x, y = node.y, r = node.radius;
  var angle = 0.6;                       // radians from vertical, about 34 degrees
  var sx = Math.sin(angle), cs = Math.cos(angle);
  return {
    ax: x - sx * r, ay: y - cs * r,      // leaves from the surface
    // Returns a head-length out, still along its own radius, so the arrow tip
    // reaches the circle while travelling perpendicular to it.
    bx: x + sx * (r + ARROW_LENGTH), by: y - cs * (r + ARROW_LENGTH),
    nx: -sx, ny: -cs,                    // outward radius at the left anchor
    mx: sx, my: -cs,                     // outward radius at the right anchor
    px: x, py: y - (r + r * 1.15),       // crown of the loop
    reach: r * 1.15, run: r * 0.62,
  };
}

function selfLoop(node) {
  var g = loopGeometry(node);
  return 'M' + g.ax + ',' + g.ay +
    'C' + (g.ax + g.nx * g.reach) + ',' + (g.ay + g.ny * g.reach) +
    ' ' + (g.px - g.run) + ',' + g.py + ' ' + g.px + ',' + g.py +
    'C' + (g.px + g.run) + ',' + g.py +
    ' ' + (g.bx + g.mx * g.reach) + ',' + (g.by + g.my * g.reach) +
    ' ' + g.bx + ',' + g.by;
}

function isNullable(type) { return /\|\s*None\s*$/.test(String(type).trim()); }

// The is-a chain above a component, nearest parent first. Shared by the graph
// and the selection so both agree on what a component abstracts to.
function ancestorNames(components, component) {
  var names = [];
  var parent = component ? component.parent : null;
  while (parent && names.indexOf(parent) < 0) {
    names.push(parent);
    var next = components.get(parent);
    parent = next ? next.parent : null;
  }
  return names;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"]/g, function (character) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[character];
  });
}

// The nearest ancestor that also declares this property, or null when the
// component declares it itself. Ancestors arrive nearest first.
function propertyOrigin(name, ancestors) {
  var found = null;
  (ancestors || []).some(function (ancestor) {
    var declares = (ancestor.properties || []).some(function (p) { return p.name === name; });
    if (declares) { found = ancestor.name; }
    return declares;
  });
  return found;
}

function propertyList(component, ancestors) {
  var properties = component.properties || [];
  if (!properties.length) { return '<h3>Properties</h3><p class="empty">None.</p>'; }
  var origins = properties.map(function (property) {
    return propertyOrigin(property.name, ancestors);
  });
  var inherited = origins.filter(Boolean).length;
  var heading = '<h3>Properties'
    + (inherited ? ' <span class="inherit-count">' + inherited + ' inherited</span>' : '')
    + '</h3>';
  return heading + properties.map(function (property, index) {
    var family = typeFamily(property.type);
    var examples = (property.examples || []).map(function (value) {
      return '<li><code class="type ' + family + '">' + escapeHtml(value) + '</code></li>';
    }).join('');
    return '<section class="property">' +
      '<div class="property-head">' +
        '<span class="property-name">' + escapeHtml(property.name) + '</span>' +
        '<span class="type ' + family + '">' + escapeHtml(property.type) + '</span>' +
        (isNullable(property.type) ? '<span class="nullable">nullable</span>' : '') +
        (origins[index] ? '<span class="inherited">from ' + escapeHtml(origins[index]) + '</span>' : '') +
      '</div>' +
      '<p class="property-desc">' + (property.description ? escapeHtml(property.description)
                                                          : '<span class="empty">No description.</span>') + '</p>' +
      (examples
        ? '<div class="examples"><span class="examples-label">Examples</span><ul class="chips">' + examples + '</ul></div>'
        : '<div class="examples"><span class="examples-label">Examples</span><p class="empty">None observed.</p></div>') +
      '</section>';
  }).join('');
}

function componentPanel(component, extra, ancestors) {
  var kind = component.kind === 'node' ? 'node component' : 'edge component';
  var counts = component.counts || { records: 0, inclusive_records: 0, bindings: 0 };
  return '<h2>' + escapeHtml(component.name) +
    '<span class="tag">' + kind + '</span>' +
    (component.abstract ? '<span class="tag">abstract</span>' : '') + '</h2>' +
    '<p>' + (component.description ? escapeHtml(component.description)
                                   : '<span class="empty">No description.</span>') + '</p>' +
    '<dl>' + (extra || '') +
    (component.parent ? '<dt>Category</dt><dd><code>' + escapeHtml(component.parent) + '</code></dd>' : '') +
    (component.endpoints ? '<dt>Endpoints</dt><dd><code>' +
      escapeHtml(component.endpoints.source) + '</code> &rarr; <code>' +
      escapeHtml(component.endpoints.target) + '</code></dd>' : '') +
    '<dt>Semantic label</dt><dd><code>' + escapeHtml(component.label) + '</code></dd>' +
    '<dt>Records</dt><dd>' + counts.records + ' of its own, ' + counts.inclusive_records +
    ' including descendants, from ' + counts.bindings + ' binding' +
    (counts.bindings === 1 ? '' : 's') + '</dd>' +
    '<dt>Symbol</dt><dd><code>' + escapeHtml(component.symbol_id) + '</code></dd>' +
    '</dl>' + propertyList(component, ancestors);
}

var EDGE_KIND_LABELS = {
  relation: 'relationship between bound components',
  category: 'category declaration over the endpoint kinds'
};

function linkPanel(link, ancestors) {
  var endpoint = function (value) {
    return '<code>' + escapeHtml(value.name || value) + '</code>';
  };
  return componentPanel(link.component,
    '<dt>Edge kind</dt><dd>' + EDGE_KIND_LABELS[link.type] + '</dd>' +
    '<dt>Connects</dt><dd>' + endpoint(link.source) + ' &rarr; ' + endpoint(link.target) + '</dd>',
    ancestors);
}
/* APP-END */

if (typeof document !== 'undefined' && typeof d3 !== 'undefined') {
  main(JSON.parse(document.getElementById('meta-graph-data').textContent));
}

function main(documentData) {
  var graph = buildGraph(documentData);
  var links = spreadLinks(graph.links.concat());
  var componentIndex = new Map(
    documentData.nodes.concat(documentData.edges).map(function (c) { return [c.name, c]; })
  );
  var panel = d3.select('#panel');
  var svg = d3.select('#svg');
  var box = document.getElementById('graph').getBoundingClientRect();

  d3.select('#totals').text(
    documentData.summary.total_nodes + ' nodes / ' + documentData.summary.total_edges +
    ' edges across ' + (documentData.summary.node_components + documentData.summary.edge_components) +
    ' components');

  // Markers are sized in user units, not stroke widths, so emphasising a link
  // cannot enlarge its head or slide it off the boundary.
  addMarker('arrow', '#6ee7b7');
  addMarker('arrow-category', '#c4a2ff');
  addMarker('arrow-associated', '#c4a2ff');
  addMarker('arrow-selected', '#ffd166');
  addMarker('arrow-hover', '#f8fafc');

  function addMarker(id, colour) {
    svg.append('defs').append('marker')
      .attr('id', id).attr('viewBox', '0 -4 ' + ARROW_LENGTH + ' 8')
      .attr('markerUnits', 'userSpaceOnUse')
      .attr('markerWidth', ARROW_LENGTH).attr('markerHeight', 8)
      // Zero puts the head's base on the path end and lets it reach forward to
      // the target. Anything larger drags the head back over the stroke, whose
      // width exceeds the cone's height near the tip and bleeds out the sides.
      .attr('refX', 0).attr('refY', 0).attr('orient', 'auto')
      .append('path').attr('d', 'M0,-4L' + ARROW_LENGTH + ',0L0,4').attr('fill', colour);
  }

  // The head is a separate painted shape, so it has to be told about emphasis
  // the same way the line is.
  function arrowFor(link, emphasis) {
    if (link.type === 'hierarchy') { return null; }
    if (emphasis) { return 'url(#arrow-' + emphasis + ')'; }
    // An unemphasised category keeps the violet head that matches its dashed
    // declaration line.
    return link.type === 'category' ? 'url(#arrow-category)' : 'url(#arrow)';
  }

  var root = svg.append('g');
  svg.call(d3.zoom().scaleExtent([0.2, 6]).on('zoom', function (event) {
    root.attr('transform', event.transform);
  }));

  var simulation = d3.forceSimulation(graph.nodes)
    .force('link', d3.forceLink(links).id(function (d) { return d.name; })
      .distance(function (link) {
        return link.type === 'hierarchy' ? 80 : link.type === 'category' ? 60 : 140;
      })
      // A declaration is information, not a constraint, so it is held loosely;
      // d3's own jiggle keeps a self-declaration from dividing by a zero length.
      .strength(function (link) { return link.type === 'hierarchy' ? 0.5 : link.type === 'category' ? 0.05 : 0.25; }))
    .force('charge', d3.forceManyBody().strength(-500))
    .force('center', d3.forceCenter(box.width / 2, box.height / 2))
    .force('collide', d3.forceCollide().radius(function (d) { return d.radius + 16; }));

  // Each link is one group holding a wide transparent hit path and the visible
  // path, so a thin curve still has a target a pointer can find.
  var linkGroup = root.append('g').selectAll('g').data(links).join('g')
    .attr('class', function (link) { return 'link-group ' + link.type; })
    .on('click', function (event, link) { event.stopPropagation(); select('link', link); })
    .on('mouseenter', function (event, link) { showHover('link', link); })
    .on('mouseleave', hideHover);
  linkGroup.append('path').attr('class', 'hit');
  linkGroup.append('path')
    .attr('class', function (link) { return 'link ' + link.type; })
    .attr('marker-end', function (link) { return arrowFor(link, ''); });
  var linkPaths = linkGroup.selectAll('path');

  // Edge names are drawn for relations and category declarations. A hierarchy
  // line is named after its child component, so giving it a label would show
  // that name twice and read as another node.
  var linkLabel = linkGroup.filter(function (link) { return link.type !== 'hierarchy'; })
    .append('text')
    .attr('class', 'link-label')
    .attr('text-anchor', 'middle')
    .attr('dy', '0.32em')
    .text(function (link) { return link.component.name; });

  // Names are hover and click targets in their own right. They only set the
  // hover; the group's mouseleave is the sole thing that clears it, so moving
  // between a name and its line does not flicker the preview.
  linkLabel
    .on('mouseenter', function (event, link) { showHover('link', link); })
    .on('click', function (event, link) { event.stopPropagation(); select('link', link); });

  var node = root.append('g').selectAll('g').data(graph.nodes).join('g')
    .attr('class', function (d) { return 'node' + (d.abstract ? ' abstract' : ''); })
    .attr('aria-label', function (d) { return d.name + ' ' + d.component.kind + ' component'; })
    .on('click', function (event, d) { event.stopPropagation(); select('node', d); })
    .on('mouseenter', function (event, d) { showHover('node', d); })
    .on('mouseleave', hideHover)
    .call(d3.drag()
      .on('start', function (event, d) {
        if (!event.active) { simulation.alphaTarget(0.3).restart(); }
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', function (event, d) { d.fx = event.x; d.fy = event.y; })
      .on('end', function (event, d) {
        if (!event.active) { simulation.alphaTarget(0); }
        d.fx = null; d.fy = null;
      }));
  node.append('circle').attr('r', function (d) { return d.radius; });
  var nodeLabel = node.append('text').attr('dy', function (d) { return d.radius + 13; })
    .attr('text-anchor', 'middle').text(function (d) { return d.name; });
  nodeLabel
    .on('mouseenter', function (event, d) { showHover('node', d); })
    .on('click', function (event, d) { event.stopPropagation(); select('node', d); });

  simulation.on('tick', function () {
    node.attr('transform', function (d) { return 'translate(' + d.x + ',' + d.y + ')'; });
    linkPaths.attr('d', function () { return curve(d3.select(this.parentNode).datum()); });
    linkLabel.attr('transform', function (link) {
      var point = labelPoint(link);
      return 'translate(' + point.x + ',' + point.y + ')';
    });
  });

  // Shared by the path and its label so the text always sits on the curve it
  // belongs to, including the fanned-out parallel cases.
  function geometry(link) {
    var ux = link.target.x - link.source.x;
    var uy = link.target.y - link.source.y;
    var length = Math.sqrt(ux * ux + uy * uy) || 1;
    ux /= length; uy /= length;
    // Trim to both boundaries so the line runs between the circles rather than
    // centre to centre underneath them. The far end gives up one head-length so
    // the stroke never extends beyond the point of the arrow.
    var head = link.type === 'hierarchy' ? 0 : ARROW_LENGTH;
    var startGap = link.source.radius + 2;
    var endGap = link.target.radius + 2 + head;
    // Two nodes pressed together leave no room for those gaps; give up the trim
    // rather than draw the line backwards through a circle.
    if (length - startGap - endGap < 4) {
      startGap = length / 2;
      endGap = length / 2;
    }
    var sx = link.source.x + ux * startGap;
    var sy = link.source.y + uy * startGap;
    var ex = link.target.x - ux * endGap;
    var ey = link.target.y - uy * endGap;
    if (!link.spread) { return { sx: sx, sy: sy, ex: ex, ey: ey, curved: false, ux: ux, uy: uy }; }
    var offset = link.spread * 28;
    return {
      sx: sx, sy: sy, ex: ex, ey: ey, curved: true, ux: ux, uy: uy,
      mx: (sx + ex) / 2 - uy * offset,
      my: (sy + ey) / 2 + ux * offset,
    };
  }

  function curve(link) {
    if (link.source === link.target) { return selfLoop(link.source); }
    var g = geometry(link);
    if (!g.curved) { return 'M' + g.sx + ',' + g.sy + 'L' + g.ex + ',' + g.ey; }
    return 'M' + g.sx + ',' + g.sy + 'Q' + g.mx + ',' + g.my + ' ' + g.ex + ',' + g.ey;
  }

  // Where an edge name goes: the middle of its own curve, lifted off the line so
  // the stroke does not strike through it.
  function labelPoint(link) {
    if (link.source === link.target) {
      var loop = loopGeometry(link.source);
      return { x: loop.px, y: loop.py - 9 };
    }
    var g = geometry(link);
    var x = g.curved ? 0.25 * g.sx + 0.5 * g.mx + 0.25 * g.ex : (g.sx + g.ex) / 2;
    var y = g.curved ? 0.25 * g.sy + 0.5 * g.my + 0.25 * g.ey : (g.sy + g.ey) / 2;
    return { x: x - g.uy * 9, y: y + g.ux * 9 };
  }

  var selected = null;   // locked by a click
  var hovered = null;    // transient preview; only the panel shows it
  var IDLE_PANEL = '<p class="empty">Select a node or an edge to inspect it.</p>';

  // Hover and click produce the same kind of view: the component picked, the
  // abstractions above it, and the neighbours it connects to. They differ in
  // persistence, not presentation.
  function focusOf(state) {
    var datum = state.datum;
    var chain = new Set(ancestorNames(componentIndex, datum.component));
    var name = state.kind === 'node' ? datum.name : null;

    var isAssociated = function (item) {
      if (item === datum) { return false; }
      if (chain.has(item.component ? item.component.name : item.name)) { return true; }
      return !!name && item.type === 'hierarchy'
        && chain.has(item.target.name)
        && (item.source.name === name || chain.has(item.source.name));
    };

    var focus = new Set(chain);
    if (name) { reachable(graph, name).forEach(focus.add, focus); }
    else { focus.add(datum.source.name); focus.add(datum.target.name); }
    links.forEach(function (link) {
      if (isAssociated(link) || link === datum) {
        focus.add(link.source.name);
        focus.add(link.target.name);
      }
    });
    if (name) { focus.add(name); }
    return { datum: datum, focus: focus, isAssociated: isAssociated };
  }

  // A hierarchy line joins declarations rather than being one, so it is never a
  // hover or selection target.
  function canHover(kind, item) {
    if (item.type === 'hierarchy') { return false; }
    if (!selected) { return true; }
    var locked = focusOf(selected);
    return item === locked.datum || locked.isAssociated(item)
      || (kind === 'node'
        ? locked.focus.has(item.name)
        : locked.focus.has(item.source.name) && locked.focus.has(item.target.name));
  }

  function showHover(kind, datum) {
    // With something locked, hovering is limited to what that lock has made
    // active, so a preview cannot reach past the current context.
    if (!canHover(kind, datum)) { return; }
    hovered = { kind: kind, datum: datum };
    apply();
  }

  function hideHover() {
    hovered = null;
    apply();
  }

  function apply() {
    // The lock and the preview are drawn together, so hovering never hides
    // where you currently are.
    var states = [selected, hovered].filter(Boolean);
    var views = states.map(focusOf);
    var focus = new Set(), primary = new Set();
    views.forEach(function (view) {
      view.focus.forEach(focus.add, focus);
      primary.add(view.datum);
    });

    var isPrimary = function (item) { return primary.has(item); };
    var isAssociated = function (item) {
      return views.some(function (view) { return view.isAssociated(item); });
    };
    // The head is a separate painted shape, so it is told about emphasis the
    // same way the line is. The lock outranks a shared abstraction so you never
    // lose your place.
    var emphasis = function (item) {
      if (hovered && hovered.datum === item) { return 'hover'; }
      if (selected && selected.datum === item) { return 'selected'; }
      return isAssociated(item) ? 'associated' : '';
    };
    var dimmed = function (item) {
      if (states.length === 0) { return false; }
      return !isPrimary(item) && !isAssociated(item);
    };

    node.classed('selected', function (d) { return !!selected && selected.datum === d; })
      .classed('hovered', function (d) { return !!hovered && hovered.datum === d; })
      .classed('associated', function (d) { return isAssociated(d) && !isPrimary(d); })
      .classed('dim', function (d) { return dimmed(d) && !focus.has(d.name); });
    linkGroup.classed('selected', function (l) { return !!selected && selected.datum === l; })
      .classed('hovered', function (l) { return !!hovered && hovered.datum === l; })
      .classed('associated', function (l) { return isAssociated(l) && !isPrimary(l); })
      .classed('dim', function (l) {
        return dimmed(l)
          && !(focus.has(l.source.name) && focus.has(l.target.name));
      });
    linkGroup.select('.link').attr('marker-end', function (l) { return arrowFor(l, emphasis(l)); });
    renderPanel();
  }

  // The component's ancestors, nearest first, so a property can be attributed to
  // the category that introduced it.
  function ancestorComponents(component) {
    return ancestorNames(componentIndex, component)
      .map(function (name) { return componentIndex.get(name); })
      .filter(Boolean);
  }

  function renderPanel() {
    var shown = hovered || selected;
    if (!shown) { panel.html(IDLE_PANEL); return; }
    var ancestors = ancestorComponents(shown.datum.component);
    panel.html(shown.kind === 'node'
      ? componentPanel(shown.datum.component, '', ancestors)
      : linkPanel(shown.datum, ancestors));
  }

  function select(kind, datum) {
    if (datum.type === 'hierarchy') { return; }
    selected = { kind: kind, datum: datum };
    apply();
  }

  svg.on('click', function () {
    selected = null;
    hovered = null;
    apply();
  });
}
</script>
</body>
</html>
"""


def _embed(document: dict[str, Any]) -> str:
    """Serialise the document for a ``<script type="application/json">`` block."""
    payload = json.dumps(document, sort_keys=True, indent=2, default=str)
    # A literal closing tag inside a string value would end the block early.
    return payload.replace("</", "<\\/")


def render(document: dict[str, Any]) -> str:
    """Render the meta graph document as one self-contained HTML page."""
    d3 = files(__package__).joinpath("static", "d3.v7.min.js").read_text(encoding="utf-8")
    return (_TEMPLATE
            .replace(_D3_MARKER, d3)
            .replace(_DATA_MARKER, _embed(document)))


__all__ = ["render"]
