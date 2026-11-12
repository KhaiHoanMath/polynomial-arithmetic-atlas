// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import vm from 'node:vm';
import { loadComments, renderComments } from './comments.mjs';

const disabled = { enabled: false, provider: 'hyvor', website_id: '', moderation_verified: false };
const enabled = { ...disabled, enabled: true, website_id: '123', moderation_verified: true };
const context = { id: 'article:fekete', title: 'Fekete polynomials', url: 'https://example.test/atlas/articles/fekete.html' };
const question = { id: 'question:fekete-prime', title: 'A question', url: 'https://example.test/atlas/questions.html#question-fekete-prime', group: 'Questions' };

async function readFixture(config) {
  const root = await mkdtemp(join(tmpdir(), 'atlas-comments-'));
  try {
    await mkdir(join(root, 'content'));
    await writeFile(join(root, 'content/comments.json'), JSON.stringify(config));
    return await loadComments(pathToFileURL(`${root}/`));
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

test('disabled configuration renders nothing and needs no thread', async () => {
  const config = await readFixture(disabled);
  assert.equal(renderComments(config), '');
  assert.ok(Object.isFrozen(config));
});

test('enabled configuration requires an ID and explicit moderation verification', async () => {
  for (const config of [
    { ...disabled, enabled: true },
    { ...enabled, moderation_verified: false },
    { ...enabled, moderation_verified: 'true' },
    { ...enabled, provider: 'giscus' },
    { ...enabled, website_id: '0' },
    { ...enabled, website_id: '-2' },
    { ...enabled, website_id: '1e3' },
    { ...enabled, website_id: ' 123' },
    { ...enabled, website_id: Number.MAX_SAFE_INTEGER + 1 },
    { ...enabled, moderation_verifed: true }
  ]) await assert.rejects(readFixture(config));
  assert.equal((await readFixture({ ...enabled, website_id: 123 })).website_id, '123');
});

test('markup escapes titles and groups and contains no provider component or script', () => {
  const title = 'A "quoted" <script>alert(1)</script> & \'test\'';
  const html = renderComments(enabled, {
    ...context, title,
    threads: [{ ...question, title, group: '\"><img src=x onerror=alert(1)>' }]
  });
  assert.ok(html.includes('&quot;quoted&quot; &lt;script&gt;alert(1)&lt;/script&gt; &amp; &#39;test&#39;'));
  assert.ok(html.includes('&quot;&gt;&lt;img src=x onerror=alert(1)&gt;'));
  assert.ok(!html.includes('<script'));
  assert.ok(!html.includes('<img'));
  assert.ok(!html.includes('<hyvor-talk-comments'));
  assert.ok(!html.includes('embed.js'));
  assert.ok(html.includes('aria-live="polite"'));
  assert.ok(html.includes('data-thread-id="article:fekete"'));
  assert.ok(html.includes('value="question:fekete-prime"'));
});

test('threads have unique stable keys and safe same-origin URLs with exact question anchors', () => {
  for (const thread of [
    { ...question, id: 'fekete-prime' },
    { ...question, id: 'question:"><script>' },
    { ...question, url: 'javascript:alert(1)' },
    { ...question, url: 'https://evil.test/#question-fekete-prime' },
    { ...question, url: 'https://user:pass@example.test/#question-fekete-prime' },
    { ...question, url: 'https://example.test/questions.html#fekete-prime' }
  ]) assert.throws(() => renderComments(enabled, { ...context, threads: [thread] }));
  assert.throws(() => renderComments(enabled, { ...context, threads: [question, question] }), /Duplicate/);
  assert.throws(() => renderComments(enabled, { ...context, threads: [{ ...context, title: 'Different' }] }), /Conflicting/);
});

// A minimal DOM harness checks the request boundary without contacting Hyvor.
class Element {
  constructor(tag = 'div') {
    this.tagName = tag;
    this.dataset = {};
    this.listeners = new Map();
    this.attributes = new Map();
    this.children = [];
    this.hidden = false;
    this.disabled = false;
    this.textContent = '';
  }
  addEventListener(type, callback, options = {}) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push({ callback, once: options.once });
  }
  removeEventListener(type, callback) {
    this.listeners.set(type, (this.listeners.get(type) ?? []).filter(item => item.callback !== callback));
  }
  dispatch(type) {
    for (const item of [...(this.listeners.get(type) ?? [])]) {
      if (item.once) this.removeEventListener(type, item.callback);
      item.callback({ target: this });
    }
  }
  setAttribute(name, value) { this.attributes.set(name, value); }
  removeAttribute(name) { this.attributes.delete(name); }
  appendChild(child) { this.children.push(child); child.parent = this; return child; }
  replaceChildren(...children) { this.children = children; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this); }
}

async function browserHarness(search = '', options = {}) {
  const source = await readFile(new URL('../static/assets/comments.js', import.meta.url), 'utf8');
  const section = new Element();
  section.dataset = { websiteId: '123', moderationVerified: 'true', threadId: context.id, threadTitle: context.title, threadUrl: context.url };
  const button = new Element('button');
  const status = new Element('p');
  const mount = new Element();
  const select = new Element('select');
  select.value = context.id;
  select.options = [context, question].map(thread => ({ value: thread.id, dataset: { threadTitle: thread.title, threadUrl: thread.url } }));
  const children = { '[data-comments-load]': button, '[data-comments-status]': status, '[data-comments-mount]': mount, '[data-comments-select]': select };
  section.querySelector = selector => children[selector];
  const head = new Element('head');
  const embeds = [];
  let define;
  let registered = false;
  const definition = new Promise(resolve => { define = () => { registered = true; resolve(); }; });
  const customElements = { get: () => registered, whenDefined: () => definition };
  const document = {
    head,
    querySelectorAll: () => [section],
    createElement: name => {
      const element = new Element(name);
      if (name === 'hyvor-talk-comments') {
        embeds.push(element);
        element.load = () => {
          element.loaded = true;
          if (!options.manualLoaded) queueMicrotask(() => element.dispatch('loaded'));
          if (options.loadingPromise) return new Promise((resolve, reject) => {
            element.rejectLoad = reject;
          });
        };
      }
      return element;
    }
  };
  const timers = new Map();
  let timerId = 0;
  const fakeTimeout = callback => { timers.set(++timerId, callback); return timerId; };
  const sandbox = { document, window: { location: { search }, customElements }, customElements, URL, URLSearchParams,
    setTimeout: fakeTimeout, clearTimeout: id => timers.delete(id) };
  vm.runInNewContext(source, sandbox);
  const flush = () => new Promise(resolve => setImmediate(resolve));
  return { section, button, status, mount, select, head, embeds, define, flush, timers };
}

test('initialization and whitelisted query selection make no third-party requests', async () => {
  const harness = await browserHarness('?thread=question%3Afekete-prime');
  assert.equal(harness.select.value, question.id);
  assert.equal(harness.head.children.length, 0);
  assert.equal(harness.embeds.length, 0);
  harness.select.value = context.id;
  harness.select.dispatch('change');
  assert.equal(harness.head.children.length, 0);
  const unknown = await browserHarness('?thread=question%3Aunknown');
  assert.equal(unknown.select.value, context.id);
  assert.equal(unknown.head.children.length, 0);
});

test('explicit click loads the module once and binds only the selected known thread', async () => {
  const harness = await browserHarness('?thread=question%3Afekete-prime');
  harness.button.dispatch('click');
  assert.equal(harness.head.children.length, 1);
  assert.equal(harness.head.children[0].src, 'https://talk.hyvor.com/embed/embed.js');
  assert.equal(harness.head.children[0].type, 'module');
  assert.equal(harness.embeds.length, 0);
  harness.define();
  await harness.flush();
  const embed = harness.embeds[0];
  assert.equal(embed.attributes.get('page-id'), question.id);
  assert.equal(embed.attributes.get('page-url'), question.url);
  assert.equal(embed.attributes.get('loading'), 'manual');
  assert.equal(JSON.parse(embed.attributes.get('settings')).editor.math, true);
  assert.equal(harness.mount.hidden, false);
  assert.equal(harness.button.hidden, true);
  harness.select.value = context.id;
  harness.select.dispatch('change');
  assert.equal(harness.mount.children.length, 0);
  assert.equal(harness.head.children.length, 1);
  assert.equal(harness.embeds.length, 1);
  harness.button.dispatch('click');
  await harness.flush();
  assert.equal(harness.head.children.length, 1);
  assert.equal(harness.embeds[1].attributes.get('page-id'), context.id);
});

test('failed script is retryable; timeout reuses the pending script', async () => {
  const failed = await browserHarness();
  failed.button.dispatch('click');
  failed.head.children[0].dispatch('error');
  await failed.flush();
  assert.equal(failed.button.textContent, 'Try again');
  assert.equal(failed.head.children.length, 0);
  failed.button.dispatch('click');
  assert.equal(failed.head.children.length, 1);
  failed.define();
  await failed.flush();
  assert.equal(failed.mount.hidden, false);

  const slow = await browserHarness();
  slow.button.dispatch('click');
  for (const callback of [...slow.timers.values()]) callback();
  await slow.flush();
  assert.equal(slow.button.textContent, 'Try again');
  slow.button.dispatch('click');
  assert.equal(slow.head.children.length, 1);
  slow.define();
  await slow.flush();
  assert.equal(slow.embeds.length, 1);
  assert.equal(slow.mount.hidden, false);
});

test('late loaded event from a timed-out component cannot replace the retried thread', async () => {
  const harness = await browserHarness('', { manualLoaded: true });
  harness.button.dispatch('click');
  harness.define();
  await harness.flush();
  const oldEmbed = harness.embeds[0];
  for (const callback of [...harness.timers.values()]) callback();
  await harness.flush();
  assert.equal(harness.button.textContent, 'Try again');
  harness.button.dispatch('click');
  await harness.flush();
  const newEmbed = harness.embeds[1];
  oldEmbed.dispatch('loaded');
  await harness.flush();
  assert.equal(harness.mount.hidden, true);
  newEmbed.dispatch('loaded');
  await harness.flush();
  assert.equal(harness.mount.hidden, false);
  assert.equal(harness.mount.children[0], newEmbed);
});

test('late load rejection belongs to its old component and cannot cancel a retry', async () => {
  const harness = await browserHarness('', { manualLoaded: true, loadingPromise: true });
  harness.button.dispatch('click');
  harness.define();
  await harness.flush();
  const oldEmbed = harness.embeds[0];
  for (const callback of [...harness.timers.values()]) callback();
  await harness.flush();
  harness.button.dispatch('click');
  await harness.flush();
  const newEmbed = harness.embeds[1];
  oldEmbed.rejectLoad(new Error('Late old request failure'));
  await harness.flush();
  assert.equal(harness.button.disabled, true);
  assert.equal(harness.mount.children[0], newEmbed);
  newEmbed.dispatch('loaded');
  await harness.flush();
  assert.equal(harness.mount.hidden, false);
  assert.equal(harness.button.hidden, true);
});
