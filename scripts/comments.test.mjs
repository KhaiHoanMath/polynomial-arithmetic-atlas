// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
import vm from 'node:vm';
import { loadComments, renderComments } from './comments.mjs';

const disabled = { enabled: false, provider: 'graphcomment', shortname: '', moderation_verified: false };
const enabled = { ...disabled, enabled: true, shortname: 'polynomial-atlas', moderation_verified: true };
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

test('enabled configuration requires a valid shortname and explicit moderation verification', async () => {
  for (const config of [
    { ...disabled, enabled: true },
    { ...enabled, moderation_verified: false },
    { ...enabled, moderation_verified: 'true' },
    { ...enabled, provider: 'giscus' },
    { ...enabled, shortname: 123 },
    { ...enabled, shortname: ' atlas' },
    { ...enabled, shortname: 'atlas/site' },
    { ...enabled, shortname: '\"><script>' },
    { ...enabled, shortname: 'a'.repeat(129) },
    { ...enabled, moderation_verifed: true },
    { ...enabled, website_id: '123' }
  ]) await assert.rejects(readFixture(config));
  assert.equal((await readFixture(enabled)).shortname, 'polynomial-atlas');
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
  assert.ok(!html.includes('<iframe'));
  assert.ok(!html.includes('gc_graphlogin.js'));
  assert.ok(html.includes('aria-live="polite"'));
  assert.ok(html.includes('data-thread-id="article:fekete"'));
  assert.ok(html.includes('value="question:fekete-prime"'));
  assert.ok(html.includes('<h2 id="comments-heading">Discussion</h2>'));
  assert.ok(html.includes('>Page or question'));
  assert.ok(renderComments(enabled, context).includes('<h2 id="comments-heading">Comments</h2>'));
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

// A minimal DOM harness checks the request boundary without contacting GraphComment.
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
  section.dataset = { shortname: 'polynomial-atlas', moderationVerified: 'true', threadId: context.id, threadTitle: context.title, threadUrl: context.url, ...options.dataset };
  const button = new Element('button');
  const status = new Element('p');
  const mount = new Element();
  mount.hidden = true;
  const select = new Element('select');
  select.value = context.id;
  select.options = [context, question].map(thread => ({ value: thread.id, dataset: { threadTitle: thread.title, threadUrl: thread.url } }));
  const children = { '[data-comments-load]': button, '[data-comments-status]': status, '[data-comments-mount]': mount, '[data-comments-select]': select };
  section.querySelector = selector => children[selector];
  const head = new Element('head');
  const initializations = [];
  const navigations = [];
  let reloads = 0;
  const document = {
    head,
    querySelectorAll: () => [section],
    createElement: name => new Element(name),
    getElementById: id => (options.questionAnchors ?? ['question-fekete-prime']).includes(id)
      ? { matches: selector => selector === 'article.question-card' && options.questionCardMatch !== false }
      : null
  };
  const timers = new Map();
  let timerId = 0;
  const fakeTimeout = callback => { timers.set(++timerId, callback); return timerId; };
  const window = { location: {
    search,
    href: options.href ?? 'https://example.test/atlas/comments.html' + search,
    assign: value => navigations.push(value),
    replace: value => navigations.push(value),
    reload: () => { reloads++; }
  } };
  const sandbox = { document, window, URL, URLSearchParams,
    setTimeout: fakeTimeout, clearTimeout: id => timers.delete(id) };
  vm.runInNewContext(source, sandbox);
  const flush = () => new Promise(resolve => setImmediate(resolve));
  const load = () => {
    window.__semio__gc_graphlogin = params => {
      initializations.push(JSON.parse(JSON.stringify(params)));
      if (options.throwInit) throw new Error('Provider error');
      if (!options.manualLoaded) queueMicrotask(() => window.onGcLoaded());
    };
    head.children.at(-1).dispatch('load');
  };
  const expire = () => { for (const callback of [...timers.values()]) callback(); };
  return { section, button, status, mount, select, head, initializations, navigations, window,
    load, flush, timers, expire, get reloads() { return reloads; } };
}

test('question comment permalinks reach the exact thread without a provider request', async () => {
  const commentId = '6af58c5db8e92d7f22db6a66';
  for (const href of [
    `https://example.test/atlas/questions.html#question-fekete-prime?comment_id=${commentId}`,
    `https://example.test/atlas/questions.html?comment_id=${commentId}#question-fekete-prime`
  ]) {
    const h = await browserHarness('', { href });
    assert.deepEqual(h.navigations, [
      `https://example.test/atlas/comments.html?thread=question%3Afekete-prime&comment_id=${commentId}#comments`
    ]);
    assert.equal(h.head.children.length, 0);
    assert.equal(h.initializations.length, 0);
    h.button.dispatch('click');
    assert.equal(h.head.children.length, 0, 'redirect stops normal comment initialization');
  }
});

test('ordinary anchors and untrusted or ambiguous comment permalinks do not redirect', async () => {
  const base = 'https://example.test/atlas/questions.html';
  const id = '6af58c5db8e92d7f22db6a66';
  const cases = [
    { href: `${base}#question-fekete-prime` },
    { href: `${base}?comment_id=${id}` },
    { href: `${base}#question-unknown?comment_id=${id}` },
    { href: `${base}#question-fekete-prime?comment_id=not-an-id` },
    { href: `${base}#question-fekete-prime?comment_id=${id}00` },
    { href: `${base}#question-fekete-prime?comment_id=javascript%3Aalert(1)` },
    { href: `${base}#question-..%2Fother?comment_id=${id}` },
    { href: `${base}#question-fekete-prime?comment_id=${id}?extra=1` },
    { href: `${base}?comment_id=${id}#question-fekete-prime?comment_id=${id}` },
    { href: `${base}?comment_id=${id}&comment_id=${id}#question-fekete-prime` },
    { href: `${base}#question-fekete-prime?comment_id=${id}&comment_id=${id}` },
    { href: `${base}#question-fekete-prime?comment_id=${id}`, questionAnchors: [] },
    { href: `${base}#question-fekete-prime?comment_id=${id}`, questionCardMatch: false },
    { href: `https://example.test/atlas/articles/fekete.html#question-fekete-prime?comment_id=${id}` },
    { href: `https://example.test/atlas/other-questions.html#question-fekete-prime?comment_id=${id}` }
  ];
  for (const options of cases) {
    const h = await browserHarness('', options);
    assert.equal(h.navigations.length, 0, options.href);
    assert.equal(h.head.children.length, 0, options.href);
    assert.equal(h.initializations.length, 0, options.href);
  }
});

test('initialization and whitelisted query selection make no third-party requests', async () => {
  const harness = await browserHarness('?thread=question%3Afekete-prime');
  assert.equal(harness.select.value, question.id);
  assert.equal(harness.head.children.length, 0);
  assert.equal(harness.initializations.length, 0);
  harness.select.value = context.id;
  harness.select.dispatch('change');
  assert.equal(harness.head.children.length, 0);
  assert.equal(harness.navigations[0], 'https://example.test/atlas/comments.html?thread=article%3Afekete#comments');
  const unknown = await browserHarness('?thread=question%3Aunknown');
  assert.equal(unknown.select.value, context.id);
  assert.equal(unknown.head.children.length, 0);
  unknown.select.value = 'question:unknown';
  unknown.select.dispatch('change');
  assert.equal(unknown.navigations.length, 0);
});

test('missing moderation verification or invalid shortname prevents loading', async () => {
  for (const dataset of [{ moderationVerified: 'false' }, { shortname: '' }, { shortname: '<script>' }]) {
    const h = await browserHarness('', { dataset });
    assert.equal(h.button.hidden, true);
    h.button.dispatch('click');
    assert.equal(h.head.children.length, 0);
  }
});

test('explicit click loads once and initializes only the selected stable thread', async () => {
  const h = await browserHarness('?thread=question%3Afekete-prime');
  h.button.dispatch('click');
  h.button.dispatch('click');
  assert.equal(h.head.children.length, 1);
  assert.equal(h.head.children[0].src, 'https://integration.graphcomment.com/gc_graphlogin.js');
  assert.equal(h.initializations.length, 0);
  h.load();
  await h.flush();
  assert.equal(h.window.onGcLoaded, h.window.__semio__onGcLoaded);
  assert.deepEqual(h.initializations, [{
    graphcommentId: 'polynomial-atlas',
    behaviour: { uid: question.id, url: question.url, sort: 'oldest' },
    statistics: { pageTitle: question.title }
  }]);
  assert.equal(h.mount.children[0].id, 'graphcomment');
  assert.equal(h.mount.hidden, false);
  assert.equal(h.button.hidden, true);
  assert.equal(h.status.textContent, `Comments for ${question.title}`);
  h.select.value = context.id;
  h.select.dispatch('change');
  assert.equal(h.navigations.length, 1);
  assert.equal(h.initializations.length, 1);
});

test('failed script is retryable; a timed-out pending script is reused', async () => {
  const failed = await browserHarness();
  failed.button.dispatch('click');
  failed.head.children[0].dispatch('error');
  await failed.flush();
  assert.equal(failed.button.textContent, 'Try again');
  assert.equal(failed.head.children.length, 0);
  failed.button.dispatch('click');
  assert.equal(failed.head.children.length, 1);
  failed.load();
  await failed.flush();
  assert.equal(failed.mount.hidden, false);

  const slow = await browserHarness();
  slow.button.dispatch('click');
  slow.expire();
  await slow.flush();
  assert.equal(slow.button.textContent, 'Try again');
  slow.button.dispatch('click');
  assert.equal(slow.head.children.length, 1);
  slow.load();
  await slow.flush();
  assert.equal(slow.initializations.length, 1);
  assert.equal(slow.mount.hidden, false);
});

test('a loader without the documented entry point fails visibly and can be retried', async () => {
  const h = await browserHarness();
  h.button.dispatch('click');
  h.head.children[0].dispatch('load');
  await h.flush();
  assert.equal(h.head.children.length, 0);
  assert.equal(h.button.textContent, 'Try again');
  assert.equal(h.mount.hidden, true);
});

test('late widget readiness cannot revive a failed mount; recovery reloads the page', async () => {
  const h = await browserHarness('', { manualLoaded: true });
  h.button.dispatch('click');
  h.load();
  await h.flush();
  assert.equal(h.button.disabled, true);
  h.expire();
  await h.flush();
  assert.equal(h.button.textContent, 'Reload page');
  assert.equal(h.mount.hidden, true);
  h.window.onGcLoaded();
  await h.flush();
  assert.equal(h.mount.hidden, true);
  assert.equal(h.button.textContent, 'Reload page');
  h.button.dispatch('click');
  assert.equal(h.reloads, 1);
  assert.equal(h.initializations.length, 1);
});

test('provider initialization failure does not retry the singleton in place', async () => {
  const h = await browserHarness('', { throwInit: true });
  h.button.dispatch('click');
  h.load();
  await h.flush();
  assert.equal(h.button.textContent, 'Reload page');
  assert.equal(h.mount.hidden, true);
  h.button.dispatch('click');
  assert.equal(h.reloads, 1);
  assert.equal(h.initializations.length, 1);
});
