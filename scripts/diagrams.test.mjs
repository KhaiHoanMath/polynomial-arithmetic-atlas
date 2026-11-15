// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';
import { auditDiagramLayout, renderDiagram, renderDiagramSVG } from './diagrams.mjs';

const root = new URL('../', import.meta.url);
const files = (await readdir(new URL('content/diagrams/', root))).filter(file => file.endsWith('.json')).sort();
const diagrams = (await Promise.all(files.map(async file => JSON.parse(await readFile(new URL(`content/diagrams/${file}`, root), 'utf8'))))).flat();
const catalogue = JSON.parse(await readFile(new URL('content/references.json', root), 'utf8'));
const byRef = new Map(catalogue.references.map(reference => [reference.id, reference]));
const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
const attribute = (tag, name) => tag.match(new RegExp(`(?:^|\\s)${name}="([^"]*)"`))?.[1];
const tags = (html, expression) => [...html.matchAll(expression)].map(match => match[0]);

test('every current diagram has separated visible boxes and fits its canvas', async context => {
  assert(diagrams.length > 0, 'the audit must exercise actual content');
  for (const diagram of diagrams) await context.test(diagram.id, () => {
    const audit = auditDiagramLayout(diagram);
    assert.equal(audit.ok, true, JSON.stringify(audit.issues, null, 2));
    assert.equal(audit.nodeCount, diagram.nodes.length);
    assert.equal(audit.edgeCount, diagram.edges.length);
    assert(audit.maxHorizontalNodes <= 4, 'no more than four nodes share a horizontal rank');
    assert(audit.longestLabel.estimatedWidth <= audit.longestLabel.availableWidth + 0.5);
    assert(audit.nodes.every(node => node.width > 0 && node.height > 0));
  });
});

test('logical edge directions and preprint styling survive SVG generation', () => {
  let equivalences = 0;
  let preprintEdges = 0;
  for (const diagram of diagrams) {
    const svg = renderDiagramSVG(diagram);
    const paths = tags(svg, /<path\b[^>]*class="dg-edge\s[^>]*>/g);
    assert.equal(paths.length, diagram.edges.length);
    paths.forEach((path, index) => {
      const edge = diagram.edges[index];
      assert(attribute(path, 'marker-end'), `${diagram.id}: every edge has its forward arrowhead`);
      assert.equal(Boolean(attribute(path, 'marker-start')), edge.type === 'equivalence', `${diagram.id}, edge ${index + 1}: only equivalences get reverse arrowheads`);
      assert.equal(attribute(path, 'class').includes('dg-edge-preprint'), Boolean(edge.preprint));
      if (edge.preprint) {
        preprintEdges++;
        assert.match(attribute(path, 'marker-end'), /preprint\)$/);
      }
      if (edge.type === 'equivalence') {
        equivalences++;
        assert.equal(attribute(path, 'marker-start'), attribute(path, 'marker-end'));
      }
      if (edge.type === 'flow') assert.match(attribute(path, 'marker-end'), /arrow-flow(?:-preprint)?\)$/);
    });
    assert.match(svg, /\.dg-edge-preprint\{[^}]*stroke-dasharray:6 4/);
    assert.match(svg, /orient="auto-start-reverse"/);
  }
  assert(equivalences > 0 && preprintEdges > 0, 'the catalogue exercises both distinctions');
});

test('every numbered connection targets exact evidence in a native collapsed disclosure', () => {
  for (const diagram of diagrams) {
    const html = renderDiagram(diagram, { base: '../', byRef });
    const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
    assert.equal(new Set(ids).size, ids.length, `${diagram.id}: unique HTML and SVG IDs`);
    for (const match of html.matchAll(/href="#(diagram-[^"]+-edge-\d+)"/g)) assert(ids.includes(match[1]), `missing evidence fragment ${match[1]}`);
    const labels = tags(html, /<a\b[^>]*class="dg-label(?: dg-label-preprint)?"[^>]*>/g);
    assert.equal(labels.length, diagram.edges.length);
    diagram.edges.forEach((edge, index) => {
      const id = `diagram-${diagram.id}-edge-${index + 1}`;
      assert.equal(attribute(labels[index], 'href'), `#${id}`);
      const row = html.match(new RegExp(`<tr id="${id}"[^>]*>([\\s\\S]*?)</tr>`))?.[1];
      assert(row, `${diagram.id}: evidence row ${index + 1}`);
      assert(row.includes(escape(edge.explanation || edge.label)), 'the mathematical meaning is visible outside the SVG');
      for (const citation of edge.citations ?? []) {
        const source = diagram.sources.find(item => item.id === citation);
        const url = source.url || byRef.get(source.key)?.url;
        assert(row.includes(escape(source.locator)), `${diagram.id}: exact theorem/version locator`);
        assert(row.includes(`href="../bibliography.html#${escape(source.key)}"`));
        assert(row.includes(`href="${escape(url)}"`), `${diagram.id}: direct primary-source link`);
      }
    });
    const disclosure = html.match(/<details class="diagram-evidence-details"[^>]*>/)?.[0];
    assert(disclosure, 'native disclosure works without scripting');
    assert(!/\sopen(?:\s|=|>)/.test(disclosure), 'evidence is initially collapsed');
    assert(html.includes(`<summary>Inspect all ${diagram.edges.length} connections and exact references</summary>`));
    assert(!html.includes('The displayed inputs are combined here;'), 'flow boilerplate is not repeated');
    assert(!/<script\b|foreignObject|\sonclick=/.test(html));
  }
});

test('the legend lists only gate and publication distinctions present in the diagram', () => {
  for (const diagram of diagrams) {
    const html = renderDiagram(diagram);
    const legend = html.match(/<p class="diagram-legend">([\s\S]*?)<\/p>/)[1];
    assert.equal(legend.includes('<b>AND</b>'), diagram.nodes.some(node => node.kind === 'gate' && node.label === 'AND'));
    assert.equal(legend.includes('<b>OR</b>'), diagram.nodes.some(node => node.kind === 'gate' && node.label === 'OR'));
    assert.equal(legend.includes('diagram-dash'), diagram.edges.some(edge => edge.preprint));
    assert.equal(legend.includes('equivalence'), diagram.edges.some(edge => edge.type === 'equivalence'));
  }
});

test('standalone SVG links resolve back to articles and the canonical evidence page', () => {
  for (const diagram of diagrams) {
    const page = `../../articles/${diagram.placements[0].article}.html`;
    const svg = renderDiagramSVG(diagram, { base: '../../', evidenceBase: page, standalone: true });
    assert(svg.startsWith('<?xml'));
    const nodeLinks = tags(svg, /<a\b[^>]*class="dg-node\s[^>]*>/g);
    assert.equal(nodeLinks.length, diagram.nodes.filter(node => node.article).length);
    for (const node of diagram.nodes.filter(node => node.article)) {
      assert(svg.includes(`href="../../articles/${node.article}.html${node.section ? `#${node.section}` : ''}"`));
    }
    diagram.edges.forEach((_, index) => assert(svg.includes(`href="${page}#diagram-${diagram.id}-edge-${index + 1}"`)));
    assert(!svg.includes('href="#diagram-'));
    assert(!/<script\b|foreignObject|@import|url\(https?:/.test(svg), 'standalone image needs no script, remote font, or remote style');
    assert.match(svg, /font-family:"DM Sans",system-ui,-apple-system,"Segoe UI",sans-serif/);
    assert.match(svg, /role="group" aria-labelledby="[^"]+" aria-describedby="[^"]+"/);
  }
});

test('multiple diagrams can be embedded on the same article without ID collisions', () => {
  const html = diagrams.map(diagram => renderDiagram(diagram, { base: '../', byRef })).join('\n');
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length);
});

test('long Unicode labels wrap while special characters remain inert SVG text', () => {
  const diagram = structuredClone(diagrams[0]);
  diagram.id = 'renderer-unicode-check';
  diagram.title = '<script>alert("label")</script> & mathematical text';
  const nonGate = diagram.nodes.find(node => node.kind !== 'gate');
  nonGate.label = '∏ₚₙαβγ'.repeat(15) + ' <script> & "quoted"';
  diagram.edges[0].label = 'Manylongwordcharacterswithoutspaces'.repeat(5);
  const audit = auditDiagramLayout(diagram);
  assert.equal(audit.ok, true, JSON.stringify(audit.issues, null, 2));
  const svg = renderDiagramSVG(diagram);
  assert(svg.includes('&lt;script&gt;'));
  assert(svg.includes('&amp;'));
  assert(!svg.includes('<script>'));
  assert(audit.nodes.find(node => node.id === nonGate.id).lines.length > 1);
  assert(audit.labels[0].lines.length > 1);
});

test('compact maps are centered without enlarging them to the full article width', () => {
  const diagram = diagrams.reduce((a, b) => auditDiagramLayout(a).width < auditDiagramLayout(b).width ? a : b);
  const audit = auditDiagramLayout(diagram);
  const svg = renderDiagramSVG(diagram);
  assert(svg.includes(`max-width:${Math.ceil(audit.width * 1.1)}px`));
  assert(svg.includes(`min-width:${Math.min(audit.width, 760)}px`));
  const cssPath = new URL('static/assets/diagrams.css', root);
  return readFile(cssPath, 'utf8').then(css => {
    assert.match(css, /\.diagram-viewport\{[^}]*overflow-x:auto/);
    assert.match(css, /\.diagram-viewport>\.diagram-svg\{[^}]*margin:auto/);
  });
});

const siteScript = await readFile(new URL('static/assets/site.js', root), 'utf8');
function disclosureHarness({ hash = '', nested = false } = {}) {
  const id = 'diagram-example-edge-2';
  const outer = nested ? { open: false, parentElement: null } : null;
  const disclosure = { open: false, parentElement: outer ? { closest: () => outer } : null };
  const calls = [];
  const frames = [];
  const target = {
    closest: selector => selector === 'details.diagram-evidence-details' ? disclosure : null,
    focus: options => calls.push(['focus', options]),
    scrollIntoView: options => calls.push(['scroll', options])
  };
  const documentEvents = new Map();
  const windowEvents = new Map();
  const listen = (map, name, callback) => {
    if (!map.has(name)) map.set(name, []);
    map.get(name).push(callback);
  };
  const location = { href: `https://example.test/articles/test.html${hash}`, hash };
  const document = {
    documentElement: { classList: { add() {} } },
    querySelector: () => null,
    querySelectorAll: selector => selector === 'details' ? [disclosure, ...(outer ? [outer] : [])] : [],
    getElementById: value => value === id ? target : null,
    addEventListener: (name, callback) => listen(documentEvents, name, callback)
  };
  const window = { addEventListener: (name, callback) => listen(windowEvents, name, callback) };
  const sandbox = { document, window, location, URL, requestAnimationFrame: callback => frames.push(callback) };
  runInNewContext(siteScript, sandbox);
  return {
    id, disclosure, outer, calls, location, frames,
    flush: () => { while (frames.length) frames.shift()(); },
    event: name => { for (const callback of windowEvents.get(name) || []) callback(); },
    click: (href, properties = {}) => {
      const link = { getAttribute: name => name === 'href' ? href : null };
      const event = { target: { closest: () => link }, button: 0, detail: 1, ...properties };
      for (const callback of documentEvents.get('click') || []) callback(event);
    }
  };
}

test('bookmarks and incoming SVG fragments open all ancestor details before scrolling', () => {
  const harness = disclosureHarness({ hash: '#diagram-example-edge-2', nested: true });
  assert.equal(harness.disclosure.open, true);
  assert.equal(harness.outer.open, true);
  assert.equal(harness.calls.length, 0, 'scroll waits for the opened layout');
  harness.flush();
  assert.equal(harness.calls[0][0], 'scroll');
  harness.disclosure.open = false;
  harness.event('hashchange');
  assert.equal(harness.disclosure.open, true);
  harness.flush();
  assert.equal(harness.calls.filter(call => call[0] === 'scroll').length, 2);
});

test('numbered keyboard links reopen an already selected fragment and transfer focus', () => {
  const harness = disclosureHarness();
  harness.click('#diagram-example-edge-2', { detail: 0 });
  assert.equal(harness.disclosure.open, true, 'click opens synchronously before native fragment navigation');
  harness.flush();
  assert.equal(harness.calls[0][0], 'focus');
  assert.equal(harness.calls[0][1].preventScroll, true);
  assert.equal(harness.calls[1][0], 'scroll');
  harness.disclosure.open = false;
  harness.location.hash = '#diagram-example-edge-2';
  harness.location.href += harness.location.hash;
  harness.click('#diagram-example-edge-2');
  assert.equal(harness.disclosure.open, true, 'repeated same-hash clicks still reveal the evidence');
});

test('unrelated, malformed, external, and modified links leave evidence unchanged', () => {
  for (const [href, properties] of [
    ['#diagram-other-edge-1', {}], ['#%E0%A4%A', {}], ['#references', {}],
    ['https://elsewhere.test/#diagram-example-edge-2', {}],
    ['other.html#diagram-example-edge-2', {}],
    ['#diagram-example-edge-2', { ctrlKey: true }],
    ['#diagram-example-edge-2', { metaKey: true }],
    ['#diagram-example-edge-2', { button: 1 }],
    ['#diagram-example-edge-2', { defaultPrevented: true }]
  ]) {
    const harness = disclosureHarness();
    harness.click(href, properties);
    assert.equal(harness.disclosure.open, false, `${href}: no unrelated disclosure change`);
    assert.equal(harness.frames.length, 0);
  }
});

test('printing expands evidence and restores the reader’s disclosure state afterward', async () => {
  const harness = disclosureHarness({ nested: true });
  harness.outer.open = true;
  harness.event('beforeprint');
  assert.equal(harness.disclosure.open, true);
  assert.equal(harness.outer.open, true);
  harness.event('afterprint');
  assert.equal(harness.disclosure.open, false);
  assert.equal(harness.outer.open, true);
  const css = await readFile(new URL('static/assets/diagrams.css', root), 'utf8');
  assert.match(css, /\.diagram-evidence-details::details-content\{[^}]*content-visibility:visible!important/);
});
