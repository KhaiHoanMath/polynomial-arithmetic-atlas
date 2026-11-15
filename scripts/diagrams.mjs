// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
// Dagre runs only during the build. Published diagrams are linked, accessible SVG.
import { graphlib, layout } from '@dagrejs/dagre';

const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[character]));
const decimal = value => Number(value.toFixed(2));
const key = value => String(value ?? '').replace(/[^a-zA-Z0-9_-]/g, '-');
const plain = value => String(value ?? '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
const byKey = (collection, id) => collection?.get ? collection.get(id) : collection?.find?.(item => item.id === id);
const articleURL = (node, base = '') => `${base}articles/${node.article}.html${node.section ? `#${node.section}` : ''}`;
const edgeAnchor = (diagram, index) => `diagram-${diagram.id}-edge-${index + 1}`;

function widthOf(text, fontSize = 14) {
  return Array.from(text).reduce((sum, char) => sum + (/\s/.test(char) ? .29 : /[ilIjtfr.,:;!'|]/.test(char) ? .32 : /[MW@%]/.test(char) ? .9 : /[^\x00-\x7f]/.test(char) ? .67 : .56), 0) * fontSize;
}

function wrap(text, maxWidth, fontSize = 14) {
  const lines = [];
  for (const paragraph of String(text).split(/\n/)) {
    let line = '';
    for (const word of paragraph.split(/\s+/).filter(Boolean)) {
      if (line && widthOf(`${line} ${word}`, fontSize) > maxWidth) {
        lines.push(line);
        line = '';
      }
      if (widthOf(word, fontSize) > maxWidth) {
        for (const char of Array.from(word)) {
          if (line && widthOf(line + char, fontSize) > maxWidth) {
            lines.push(line);
            line = '';
          }
          line += char;
        }
      } else line += `${line ? ' ' : ''}${word}`;
    }
    if (line) lines.push(line);
  }
  return lines.length ? lines : [''];
}

// Longest-path layers are also used to wrap an unusually wide source layer.
// These invisible layout constraints do not add mathematical relationships.
function constrainWideLayers(graph, diagram) {
  if (!graphlib.alg.isAcyclic(graph)) return;
  const levels = new Map();
  const ranks = new Map();
  for (const id of graphlib.alg.topsort(graph)) {
    const rank = Math.max(0, ...(graph.predecessors(id) ?? []).map(previous => (ranks.get(previous) ?? 0) + 1));
    ranks.set(id, rank);
    if (!levels.has(rank)) levels.set(rank, []);
    levels.get(rank).push(id);
  }
  const order = new Map(diagram.nodes.map((node, index) => [node.id, index]));
  for (const layer of levels.values()) {
    layer.sort((a, b) => order.get(a) - order.get(b));
    for (let index = 4; index < layer.length; index += 4) {
      for (const previous of layer.slice(index - 4, index)) {
        for (const next of layer.slice(index, index + 4)) {
          graph.setEdge(previous, next, { minlen: 1, weight: 2, width: 0, height: 0 }, `layout-${previous}-${next}`);
        }
      }
    }
  }
}

function graphLayout(diagram) {
  const graph = new graphlib.Graph({ multigraph: true });
  graph.setGraph({ rankdir: 'TB', ranker: 'network-simplex', nodesep: 35, edgesep: 18, ranksep: 39, marginx: 26, marginy: 25 });
  graph.setDefaultEdgeLabel(() => ({}));
  for (const node of diagram.nodes) {
    const gate = node.kind === 'gate';
    const width = gate ? 68 : 198;
    const lines = wrap(node.label, width - 30, gate ? 12 : 14);
    graph.setNode(node.id, { ...node, width, height: gate ? 48 : Math.max(58, lines.length * 19 + 28), lines });
  }
  diagram.edges.forEach((edge, index) => {
    const label = `${edge.label || (edge.type === 'equivalence' ? 'equivalent' : edge.type === 'flow' ? 'input' : 'implies')} [${index + 1}]`;
    const lines = wrap(label, 135, 11.5);
    graph.setEdge(edge.from, edge.to, {
      ...edge, index, lines,
      width: Math.max(35, ...lines.map(line => widthOf(line, 11.5))) + 14,
      height: lines.length * 15 + 9,
      minlen: 1, weight: edge.type === 'equivalence' ? 2 : 1,
      labelpos: 'c', labeloffset: 8
    }, String(index));
  });
  constrainWideLayers(graph, diagram);
  layout(graph);
  return graph;
}

const rectangle = (id, type, item) => ({
  id, type, x: item.x - item.width / 2, y: item.y - item.height / 2,
  width: item.width, height: item.height, lines: [...item.lines]
});

/**
 * Geometric build-time QA, independent of a browser or font-rendering engine.
 * Bounds use the actual Dagre node and label positions. Text widths are estimates
 * with a small safety margin, not a substitute for inspecting the rendered type.
 * The returned boxes also make a failure concrete for content authors.
 */
export function auditDiagramLayout(diagram, { tolerance = 0.5 } = {}) {
  const graph = graphLayout(diagram);
  const width = Math.ceil(graph.graph().width);
  const height = Math.ceil(graph.graph().height);
  const nodes = diagram.nodes.map(node => ({ ...rectangle(node.id, 'node', graph.node(node.id)), kind: node.kind }));
  const labels = diagram.edges.map((edge, index) => {
    const item = graph.edge(edge.from, edge.to, String(index));
    return rectangle(`edge-${index + 1}`, 'label', {
      ...item,
      x: item.x ?? item.points[Math.floor(item.points.length / 2)].x,
      y: item.y ?? item.points[Math.floor(item.points.length / 2)].y
    });
  });
  const issues = [];
  const overlap = (a, b, type) => {
    const horizontal = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
    const vertical = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
    if (horizontal > tolerance && vertical > tolerance) {
      issues.push({ type, first: a.id, second: b.id, width: decimal(horizontal), height: decimal(vertical) });
    }
  };
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) overlap(nodes[i], nodes[j], 'node-node-overlap');
  }
  for (let i = 0; i < labels.length; i++) {
    for (const node of nodes) overlap(labels[i], node, 'label-node-overlap');
    for (let j = i + 1; j < labels.length; j++) overlap(labels[i], labels[j], 'label-label-overlap');
  }
  let longestLabel = { text: '', estimatedWidth: 0, availableWidth: 0, id: '' };
  for (const item of [...nodes, ...labels]) {
    if (![item.x, item.y, item.width, item.height].every(Number.isFinite)) {
      issues.push({ type: 'nonfinite-geometry', id: item.id });
      continue;
    }
    if (item.x < -tolerance || item.y < -tolerance || item.x + item.width > width + tolerance || item.y + item.height > height + tolerance) {
      issues.push({ type: 'outside-canvas', id: item.id, x: decimal(item.x), y: decimal(item.y), width: decimal(item.width), height: decimal(item.height) });
    }
    const fontSize = item.type === 'label' ? 11.5 : item.kind === 'gate' ? 12 : 14;
    const availableWidth = item.width - (item.type === 'label' ? 6 : 16);
    for (const line of item.lines) {
      // Result nodes are semibold. Reserve extra width for weight and fallback glyphs.
      const estimatedWidth = widthOf(line, fontSize) * (item.type === 'node' ? 1.07 : 1.03);
      if (estimatedWidth > availableWidth + tolerance) {
        issues.push({ type: 'text-width', id: item.id, line, estimatedWidth: decimal(estimatedWidth), availableWidth: decimal(availableWidth) });
      }
      if (item.type === 'label' && estimatedWidth > longestLabel.estimatedWidth) {
        longestLabel = { text: line, estimatedWidth: decimal(estimatedWidth), availableWidth: decimal(availableWidth), id: item.id };
      }
    }
    const lineHeight = item.type === 'label' ? 15 : 19;
    if (item.lines.length * lineHeight > item.height) issues.push({ type: 'text-height', id: item.id });
  }
  const layers = new Map();
  for (const node of nodes) {
    const center = decimal(node.y + node.height / 2);
    if (!layers.has(center)) layers.set(center, []);
    layers.get(center).push(node.id);
  }
  const maxHorizontalNodes = Math.max(0, ...[...layers.values()].map(layer => layer.length));
  if (maxHorizontalNodes > 4) issues.push({ type: 'wide-node-layer', nodes: [...layers.values()].find(layer => layer.length > 4) });
  return { id: diagram.id, ok: issues.length === 0, width, height, nodeCount: nodes.length, edgeCount: labels.length, maxHorizontalNodes, longestLabel, issues, nodes, labels };
}

function gateEndpoint(node, point) {
  if (node.kind !== 'gate') return point;
  const dx = point.x - node.x;
  const dy = point.y - node.y;
  const denominator = Math.abs(dx) / (node.width / 2) + Math.abs(dy) / (node.height / 2);
  return denominator ? { x: node.x + dx / denominator, y: node.y + dy / denominator } : point;
}

function pathData(points) {
  return points.map((point, index) => `${index ? 'L' : 'M'}${decimal(point.x)},${decimal(point.y)}`).join(' ');
}

const svgStyle = `
.diagram-svg{font-family:"DM Sans",system-ui,-apple-system,"Segoe UI",sans-serif;background:#fffefa;color:#192f2a}
.diagram-svg .dg-edge{fill:none;stroke:#426e5c;stroke-width:1.65;stroke-linejoin:round;stroke-linecap:round}
.diagram-svg .dg-edge-flow{stroke:#7b887d;stroke-width:1.4}
.diagram-svg .dg-edge-preprint{stroke:#96662d;stroke-dasharray:6 4}
.diagram-svg .dg-node-shape{fill:#fffefa;stroke:#879e8a;stroke-width:1.3}
.diagram-svg .dg-node-method .dg-node-shape{fill:#eef1e8;stroke:#849d7e}
.diagram-svg .dg-node-result .dg-node-shape{fill:#245e4b;stroke:#245e4b}
.diagram-svg .dg-node-hypothesis .dg-node-shape{fill:#faf0dc;stroke:#b69660}
.diagram-svg .dg-node-gate .dg-node-shape{fill:#f8f6f0;stroke:#a8b39e}
.diagram-svg .dg-node-text{fill:#192f2a;font-size:14px;font-weight:500}
.diagram-svg .dg-node-result .dg-node-text{fill:#fffefa;font-weight:600}
.diagram-svg .dg-node-gate .dg-node-text{font-size:12px;font-weight:700;letter-spacing:.6px}
.diagram-svg .dg-node-link .dg-node-text{text-decoration:underline;text-decoration-color:#92ab9b;text-underline-offset:3px}
.diagram-svg .dg-node-result.dg-node-link .dg-node-text{text-decoration-color:#b9cdbc}
.diagram-svg .dg-label-back{fill:#fffefa;stroke:#d9ded2;stroke-width:.8}
.diagram-svg .dg-label-text{fill:#355c4b;font-size:11.5px;font-weight:500}
.diagram-svg .dg-label-preprint .dg-label-text{fill:#80541f}
.diagram-svg a:hover .dg-node-shape,.diagram-svg a:focus .dg-node-shape{stroke:#b46b30;stroke-width:2.4}
.diagram-svg a:hover .dg-label-back,.diagram-svg a:focus .dg-label-back{stroke:#b46b30;stroke-width:1.7}
.diagram-svg a:focus{outline:none}
`;

/**
 * Render an independent SVG. `base` is relative to the SVG's own location.
 * `evidenceBase` is the page URL (without fragment) containing its evidence table.
 */
export function renderDiagramSVG(diagram, { base = '', evidenceBase = '', standalone = false } = {}) {
  const graph = graphLayout(diagram);
  const prefix = `dg-${key(diagram.id)}`;
  const width = Math.ceil(graph.graph().width);
  const height = Math.ceil(graph.graph().height);
  const titleId = `${prefix}-title`;
  const descId = `${prefix}-description`;
  const nodes = new Map(diagram.nodes.map(node => [node.id, node]));
  const description = `${plain(diagram.summary)} ${diagram.edges.map((edge, index) => `Connection ${index + 1}: ${nodes.get(edge.from)?.label} ${edge.type === 'equivalence' ? 'is equivalent to' : edge.type === 'flow' ? 'is an input to' : 'leads to'} ${nodes.get(edge.to)?.label}. ${edge.explanation ?? ''}${edge.preprint ? ' Preprint claim.' : ''}`).join(' ')}`;
  const markers = ['published', 'preprint', 'flow', 'flow-preprint'].map(kind => {
    const open = kind.startsWith('flow');
    const color = kind.includes('preprint') ? '#96662d' : open ? '#7b887d' : '#426e5c';
    return `<marker id="${prefix}-arrow-${kind}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1 1L9 5L1 9${open ? '' : 'Z'}" fill="${open ? 'none' : color}" stroke="${color}" stroke-width="1.2"/></marker>`;
  }).join('');
  const edges = diagram.edges.map((edge, index) => {
    const positioned = graph.edge(edge.from, edge.to, String(index));
    const points = positioned.points.map(point => ({ ...point }));
    points[0] = gateEndpoint(graph.node(edge.from), points[1] ?? points[0]);
    points[points.length - 1] = gateEndpoint(graph.node(edge.to), points.at(-2) ?? points.at(-1));
    // Only gate endpoints need replacing: ordinary endpoints already meet their boxes.
    if (graph.node(edge.from).kind !== 'gate') points[0] = positioned.points[0];
    if (graph.node(edge.to).kind !== 'gate') points[points.length - 1] = positioned.points.at(-1);
    const marker = `${prefix}-arrow-${edge.type === 'flow' ? (edge.preprint ? 'flow-preprint' : 'flow') : (edge.preprint ? 'preprint' : 'published')}`;
    return `<path class="dg-edge dg-edge-${escape(edge.type)}${edge.preprint ? ' dg-edge-preprint' : ''}" d="${pathData(points)}" marker-end="url(#${marker})"${edge.type === 'equivalence' ? ` marker-start="url(#${marker})"` : ''}/>`;
  }).join('');
  const boxes = diagram.nodes.map(node => {
    const p = graph.node(node.id);
    const x = decimal(p.x - p.width / 2);
    const y = decimal(p.y - p.height / 2);
    const shape = node.kind === 'gate'
      ? `<path class="dg-node-shape" d="M${decimal(p.x)},${y}L${decimal(p.x + p.width / 2)},${decimal(p.y)}L${decimal(p.x)},${decimal(p.y + p.height / 2)}L${x},${decimal(p.y)}Z"/>`
      : `<rect class="dg-node-shape" x="${x}" y="${y}" width="${p.width}" height="${p.height}" rx="9"/>`;
    const text = `<text class="dg-node-text" text-anchor="middle" x="${decimal(p.x)}" y="${decimal(p.y - (p.lines.length - 1) * 9.5 + 4.5)}">${p.lines.map((line, index) => `<tspan x="${decimal(p.x)}" dy="${index ? 19 : 0}">${escape(line)}</tspan>`).join('')}</text>`;
    const classes = `dg-node dg-node-${escape(node.kind || 'object')}${node.article ? ' dg-node-link' : ''}`;
    return node.article
      ? `<a class="${classes}" href="${escape(articleURL(node, base))}" tabindex="0" aria-label="${escape(`${node.label}: read the related article`)}"><title>${escape(node.label)} — related article</title>${shape}${text}</a>`
      : `<g class="${classes}"><title>${escape(node.label)}</title>${shape}${text}</g>`;
  }).join('');
  const labels = diagram.edges.map((edge, index) => {
    const p = graph.edge(edge.from, edge.to, String(index));
    const x = p.x ?? p.points[Math.floor(p.points.length / 2)].x;
    const y = p.y ?? p.points[Math.floor(p.points.length / 2)].y;
    return `<a class="dg-label${edge.preprint ? ' dg-label-preprint' : ''}" href="${escape(evidenceBase)}#${edgeAnchor(diagram, index)}" tabindex="0" aria-label="${escape(`Evidence for connection ${index + 1}: ${edge.explanation || edge.label}`)}"><title>${escape(`Connection ${index + 1}: ${edge.explanation || edge.label}`)}</title><rect class="dg-label-back" x="${decimal(x - p.width / 2)}" y="${decimal(y - p.height / 2)}" width="${decimal(p.width)}" height="${p.height}" rx="4"/><text class="dg-label-text" x="${decimal(x)}" y="${decimal(y - (p.lines.length - 1) * 7.5 + 4)}" text-anchor="middle">${p.lines.map((line, lineIndex) => `<tspan x="${decimal(x)}" dy="${lineIndex ? 15 : 0}">${escape(line)}</tspan>`).join('')}</text></a>`;
  }).join('');
  return `${standalone ? '<?xml version="1.0" encoding="UTF-8"?>\n' : ''}<svg xmlns="http://www.w3.org/2000/svg" class="diagram-svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="group" aria-labelledby="${titleId}" aria-describedby="${descId}"${standalone ? '' : ` style="min-width:${Math.min(width, 760)}px;max-width:${Math.ceil(width * 1.1)}px"`}><title id="${titleId}">${escape(diagram.title)}</title><desc id="${descId}">${escape(description)}</desc><defs>${markers}</defs><style>${svgStyle}</style><rect width="${width}" height="${height}" fill="#fffefa"/>${edges}${boxes}${labels}</svg>`;
}

/** Render the article block, including visible evidence for every numbered arrow. */
export function renderDiagram(diagram, { base = '', byRef, byId, prose = escape, math = value => value, svgHref = `${base}assets/diagrams/${diagram.id}.svg` } = {}) {
  const sources = new Map(diagram.sources.map(source => [source.id, source]));
  const nodes = new Map(diagram.nodes.map(node => [node.id, node]));
  const sourceMarkup = sourceId => {
    const source = sources.get(sourceId);
    if (!source) throw Error(`Unknown source ${sourceId} in diagram ${diagram.id}`);
    const reference = byKey(byRef, source.key);
    if (byRef && !reference) throw Error(`Unknown bibliography key ${source.key} in diagram ${diagram.id}`);
    const url = source.url || reference?.url;
    const authors = String(reference?.authors || reference?.editors || '').split(/\s+and\s+/).filter(Boolean).map(name => name.split(',')[0].trim());
    const names = authors.length > 3 ? `${authors[0]} et al.` : authors.join('–');
    const shortCitation = names ? `${names}${reference?.year ? ` (${reference.year})` : ''}` : source.key;
    return `<li><a class="diagram-source-key" href="${base}bibliography.html#${escape(source.key)}"${reference?.title ? ` title="${escape(reference.title)}"` : ''}>${escape(source.id)} · ${escape(shortCitation)}</a><span class="diagram-source-locator">${prose(source.locator)}</span>${source.note ? `<span class="diagram-source-note">${prose(source.note)}</span>` : ''}${url ? `<a class="diagram-primary-source" href="${escape(url)}">Primary source ↗</a>` : ''}</li>`;
  };
  const table = `<div class="diagram-evidence-scroll" tabindex="0" role="region" aria-label="Evidence for ${escape(diagram.title)}"><table class="diagram-evidence"><caption>Evidence for each connection</caption><thead><tr><th scope="col">Connection</th><th scope="col">Statement and source</th></tr></thead><tbody>${diagram.edges.map((edge, index) => `<tr id="${edgeAnchor(diagram, index)}" tabindex="-1"><th scope="row"><span class="diagram-edge-number">${index + 1}</span><span>${escape(nodes.get(edge.from)?.label)} <span aria-label="${edge.type === 'equivalence' ? 'is equivalent to' : edge.type === 'flow' ? 'is an input to' : 'implies'}">${edge.type === 'equivalence' ? '↔' : '→'}</span> ${escape(nodes.get(edge.to)?.label)}</span><span class="diagram-edge-kind">${edge.type === 'flow' ? 'Construction / input' : edge.type === 'equivalence' ? 'Equivalence' : 'Deduction'}${edge.preprint ? ' · preprint' : ''}</span></th><td><p>${prose(edge.explanation || edge.label)}</p>${edge.citations?.length ? `<ul class="diagram-evidence-sources">${edge.citations.map(sourceMarkup).join('')}</ul>` : ''}</td></tr>`).join('')}</tbody></table></div>`;
  const evidence = `<details class="diagram-evidence-details" id="diagram-${escape(diagram.id)}-evidence"><summary>Inspect all ${diagram.edges.length} connections and exact references</summary>${table}</details>`;
  const related = (diagram.related ?? []).map(item => {
    const article = byKey(byId, item.article);
    return `<li><a href="${escape(articleURL(item, base))}">${prose(item.label || article?.title || item.article)}</a></li>`;
  }).join('');
  const status = diagram.status === 'Claimed' ? 'Claimed · preprint' : diagram.status;
  const legend = [
    '<span><b aria-hidden="true">→</b> deduction or information flow</span>',
    diagram.edges.some(edge => edge.type === 'equivalence') ? '<span><b aria-hidden="true">↔</b> equivalence</span>' : '',
    diagram.edges.some(edge => edge.preprint) ? '<span><i class="diagram-dash" aria-hidden="true"></i> preprint claim</span>' : '',
    diagram.nodes.some(node => node.kind === 'gate' && node.label === 'AND') ? '<span><b>AND</b> joint hypotheses</span>' : '',
    diagram.nodes.some(node => node.kind === 'gate' && node.label === 'OR') ? '<span><b>OR</b> alternatives</span>' : ''
  ].join('');
  return `<section class="article-diagram" id="diagram-${escape(diagram.id)}" aria-labelledby="diagram-${escape(diagram.id)}-heading"><div class="diagram-heading"><p class="eyebrow">Connections and evidence</p><span class="diagram-status diagram-status-${escape(diagram.status.toLowerCase())}">${escape(status)}</span></div><h3 id="diagram-${escape(diagram.id)}-heading">${prose(diagram.title)}</h3><p class="diagram-summary">${prose(diagram.summary)}</p><p class="diagram-scope"><strong>Scope.</strong> ${prose(diagram.scope)}</p><figure class="diagram-figure"><div class="diagram-viewport" tabindex="0" role="region" aria-label="Scrollable diagram: ${escape(diagram.title)}">${renderDiagramSVG(diagram, { base })}</div><figcaption><span>Linked nodes open articles; numbered connections open the evidence below.</span><a href="${escape(svgHref)}">Open full-size diagram ↗</a></figcaption></figure><p class="diagram-legend">${legend}</p><div class="diagram-theorem">${math(diagram.body || '')}</div>${evidence}${related ? `<div class="diagram-related"><strong>Continue reading</strong><ul>${related}</ul></div>` : ''}<p class="diagram-checked">Sources and scope checked <time datetime="${escape(diagram.checked)}">${escape(diagram.checked)}</time>.</p></section>`;
}
