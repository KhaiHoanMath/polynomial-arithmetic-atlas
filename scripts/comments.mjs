// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
import { readFile } from 'node:fs/promises';

const keys = new Set(['enabled', 'provider', 'website_id', 'moderation_verified']);
const threadPattern = /^(?:page|article|question):[a-z0-9]+(?:[._:-][a-z0-9]+)*$/;
const escapeHTML = value => String(value).replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[character]));

function validateConfig(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Comments configuration must be an object.');
  }
  for (const key of Object.keys(value)) {
    if (!keys.has(key)) throw new Error(`Unknown comments configuration key: ${key}`);
  }
  if (typeof value.enabled !== 'boolean' || typeof value.moderation_verified !== 'boolean') {
    throw new Error('Comments enabled and moderation_verified must be booleans.');
  }
  if (value.provider !== 'hyvor') throw new Error('Only the hyvor comments provider is supported.');
  const websiteId = typeof value.website_id === 'number' && Number.isSafeInteger(value.website_id)
    ? String(value.website_id) : value.website_id;
  if (typeof websiteId !== 'string' || (websiteId !== '' && !/^[1-9]\d*$/.test(websiteId))) {
    throw new Error('Comments website_id must be blank or a positive decimal integer.');
  }
  if (value.enabled && (!websiteId || !value.moderation_verified)) {
    throw new Error('Enabling comments requires a website_id and completed moderation verification.');
  }
  return Object.freeze({
    enabled: value.enabled,
    provider: 'hyvor',
    website_id: websiteId,
    moderation_verified: value.moderation_verified
  });
}

/** Read the repository configuration. Invalid settings stop the build. */
export async function loadComments(rootURL) {
  const file = new URL('content/comments.json', rootURL);
  return validateConfig(JSON.parse(await readFile(file, 'utf8')));
}

function validateThread(value, origin) {
  if (!value || typeof value !== 'object' || !threadPattern.test(value.id)) {
    throw new Error('Comment thread IDs must use a stable page:, article:, or question: key.');
  }
  if (typeof value.title !== 'string' || !value.title.trim()) {
    throw new Error(`Missing title for comment thread ${value.id}.`);
  }
  if (typeof value.url !== 'string') throw new Error(`Missing URL for comment thread ${value.id}.`);
  const url = new URL(value.url);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    throw new Error(`Unsafe URL for comment thread ${value.id}.`);
  }
  if (origin && url.origin !== origin) throw new Error('Comment threads must belong to the same site.');
  if (value.id.startsWith('question:') && url.hash !== `#question-${value.id.slice(9)}`) {
    throw new Error(`Question thread ${value.id} must link to its question- anchor.`);
  }
  if (value.group !== undefined && (typeof value.group !== 'string' || !value.group.trim())) {
    throw new Error(`Invalid group for comment thread ${value.id}.`);
  }
  return { id: value.id, title: value.title, url: url.href, group: value.group ?? 'Topics' };
}

/** Render once per page. No provider script or component is emitted here. */
export function renderComments(config, { id, title, url, threads } = {}) {
  config = validateConfig(config);
  if (!config.enabled) return '';
  const context = validateThread({ id, title, url, group: 'This page' });
  const origin = new URL(context.url).origin;
  if (threads !== undefined && !Array.isArray(threads)) throw new Error('Comment threads must be an array.');
  const supplied = (threads ?? []).map(thread => validateThread(thread, origin));
  const seen = new Set();
  for (const thread of supplied) {
    if (seen.has(thread.id)) throw new Error(`Duplicate comment thread ${thread.id}.`);
    seen.add(thread.id);
    if (thread.id === context.id && (thread.url !== context.url || thread.title !== context.title)) {
      throw new Error(`Conflicting context for comment thread ${thread.id}.`);
    }
  }
  const choices = seen.has(context.id) ? supplied : [context, ...supplied];
  const groups = new Map();
  for (const thread of choices) {
    if (!groups.has(thread.group)) groups.set(thread.group, []);
    groups.get(thread.group).push(thread);
  }
  const selector = threads !== undefined ? `<label class="comments-topic" for="comments-topic">Discussion
    <select id="comments-topic" data-comments-select>${[...groups].map(([group, members]) =>
      `<optgroup label="${escapeHTML(group)}">${members.map(thread =>
        `<option value="${escapeHTML(thread.id)}" data-thread-title="${escapeHTML(thread.title)}" data-thread-url="${escapeHTML(thread.url)}"${thread.id === context.id ? ' selected' : ''}>${escapeHTML(thread.title)}</option>`
      ).join('')}</optgroup>`
    ).join('')}</select></label>` : '';
  return `<section id="comments" class="comments-section container narrow" data-comments data-website-id="${escapeHTML(config.website_id)}" data-moderation-verified="true" data-thread-id="${escapeHTML(context.id)}" data-thread-title="${escapeHTML(context.title)}" data-thread-url="${escapeHTML(context.url)}" aria-labelledby="comments-heading">
    <h2 id="comments-heading">Comments</h2>
    <p id="comments-notice" class="comments-notice">Comments appear after the site owner approves them. Showing comments connects to Hyvor Talk. <a href="https://hyvor.com/talk/privacy" rel="noopener noreferrer">Privacy policy</a>.</p>
    ${selector}
    <button class="button button-outline comments-load" type="button" data-comments-load aria-describedby="comments-notice" aria-controls="comments-mount">Show comments</button>
    <p class="comments-status" data-comments-status role="status" aria-live="polite" aria-atomic="true"></p>
    <div id="comments-mount" class="comments-mount" data-comments-mount hidden></div>
    <noscript><p>JavaScript is required to show comments.</p></noscript>
  </section>`;
}
