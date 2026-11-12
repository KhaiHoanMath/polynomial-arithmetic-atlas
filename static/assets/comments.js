// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
(() => {
  'use strict';
  // GraphComment can append ?comment_id after a question's fragment. Route
  // those permalinks to the question thread before any provider request.
  function redirectQuestionPermalink() {
    const source = new URL(window.location.href);
    if (!/^https?:$/.test(source.protocol) || !source.pathname.endsWith('/questions.html')) return false;
    const [anchor, fragmentQuery = '', ...extra] = source.hash.slice(1).split('?');
    const match = /^question-([a-z0-9]+(?:[._:-][a-z0-9]+)*)$/.exec(anchor);
    if (!match || extra.length) return false;
    const card = document.getElementById(anchor);
    if (!card?.matches('article.question-card')) return false;
    const ids = [...source.searchParams.getAll('comment_id'),
      ...new URLSearchParams(fragmentQuery).getAll('comment_id')];
    if (ids.length !== 1 || !/^[a-f0-9]{24}$/i.test(ids[0])) return false;
    const destination = new URL('comments.html', source);
    destination.search = '';
    destination.searchParams.set('thread', `question:${match[1]}`);
    destination.searchParams.set('comment_id', ids[0]);
    destination.hash = 'comments';
    window.location.replace(destination.href);
    return true;
  }

  if (redirectQuestionPermalink()) return;

  const scriptURL = 'https://integration.graphcomment.com/gc_graphlogin.js';
  const timeoutMs = 20000;
  let providerReady;

  function withTimeout(promise) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Comments request timed out.')), timeoutMs);
      promise.then(value => { clearTimeout(timer); resolve(value); }, error => {
        clearTimeout(timer);
        reject(error);
      });
    });
  }

  function loadProvider() {
    if (typeof window.__semio__gc_graphlogin === 'function') return Promise.resolve();
    if (!providerReady) {
      providerReady = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = scriptURL;
        script.async = true;
        script.dataset.commentsProvider = 'graphcomment';
        const failed = () => {
          script.remove();
          providerReady = undefined;
          reject(new Error('Comments script could not load.'));
        };
        script.addEventListener('error', failed, { once: true });
        script.addEventListener('load', () => {
          if (typeof window.__semio__gc_graphlogin !== 'function') return failed();
          resolve();
        }, { once: true });
        document.head.appendChild(script);
      });
    }
    // Reuse a slow request on retry; never insert a second pending loader.
    return withTimeout(providerReady);
  }

  function readThread(id, title, url) {
    if (!/^(?:page|article|question):[a-z0-9]+(?:[._:-][a-z0-9]+)*$/.test(id) || !title || !url) {
      throw new Error('Invalid comment thread.');
    }
    const parsed = new URL(url);
    if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
      throw new Error('Invalid comment URL.');
    }
    if (id.startsWith('question:') && parsed.hash !== `#question-${id.slice(9)}`) {
      throw new Error('Invalid question anchor.');
    }
    return { id, title, url: parsed.href };
  }

  function setup(section) {
    const button = section.querySelector('[data-comments-load]');
    const status = section.querySelector('[data-comments-status]');
    const mount = section.querySelector('[data-comments-mount]');
    const select = section.querySelector('[data-comments-select]');
    if (!button || !status || !mount) return;
    const shortname = section.dataset.shortname;
    let current;
    const threads = new Map();
    try {
      if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(shortname ?? '') || section.dataset.moderationVerified !== 'true') {
        throw new Error('Comments have not been configured.');
      }
      current = readThread(section.dataset.threadId, section.dataset.threadTitle, section.dataset.threadUrl);
      threads.set(current.id, current);
      for (const option of select?.options ?? []) {
        const thread = readThread(option.value, option.dataset.threadTitle, option.dataset.threadUrl);
        if (new URL(thread.url).origin !== new URL(current.url).origin) throw new Error('Invalid thread origin.');
        if (threads.has(thread.id) && JSON.stringify(threads.get(thread.id)) !== JSON.stringify(thread)) {
          throw new Error('Conflicting comment threads.');
        }
        threads.set(thread.id, thread);
      }
      const requested = new URLSearchParams(window.location.search).get('thread');
      if (requested && threads.has(requested)) {
        current = threads.get(requested);
        if (select) select.value = requested;
      }
    } catch {
      button.hidden = true;
      if (select) select.disabled = true;
      status.textContent = 'Comments are not available.';
      return;
    }

    // GraphComment uses a page-wide loader. Navigate when changing discussions
    // so a delayed callback can never display the previous discussion's thread.
    select?.addEventListener('change', () => {
      const next = threads.get(select.value);
      if (!next || next.id === current.id) return;
      const destination = new URL(window.location.href);
      destination.searchParams.set('thread', next.id);
      destination.hash = 'comments';
      window.location.assign(destination.href);
    });

    let initialized = false;
    let reloadRequired = false;
    button.addEventListener('click', async () => {
      if (button.disabled) return;
      if (reloadRequired) {
        window.location.reload();
        return;
      }
      button.disabled = true;
      if (select) select.disabled = true;
      section.setAttribute('aria-busy', 'true');
      status.textContent = 'Loading comments…';
      let finishEmbed;
      try {
        const ready = new Promise((resolve, reject) => {
          let settled = false;
          let timer;
          finishEmbed = error => {
            if (settled) return;
            settled = true;
            clearTimeout(timer);
            error ? reject(error) : resolve();
          };
          // The provider invokes this callback when its widget is ready.
          // It is registered before the provider script runs, as documented.
          window.onGcLoaded = () => {
            if (initialized) finishEmbed();
          };
          // The provider's CSP guide documents this name for custom init scripts.
          window.__semio__onGcLoaded = window.onGcLoaded;
          // Start the widget timeout only after the loader has completed.
          finishEmbed.startTimer = () => {
            timer = setTimeout(() => finishEmbed(new Error('Comments did not finish loading.')), timeoutMs);
          };
        });
        // Attach a rejection handler before the asynchronous loader can fail.
        ready.catch(() => {});
        await loadProvider();
        const container = document.createElement('div');
        container.id = 'graphcomment';
        mount.replaceChildren(container);
        mount.hidden = false;
        initialized = true;
        finishEmbed.startTimer();
        window.__semio__gc_graphlogin({
          graphcommentId: shortname,
          behaviour: { uid: current.id, url: current.url, sort: 'oldest' },
          statistics: { pageTitle: current.title }
        });
        await ready;
        button.hidden = true;
        status.textContent = `Comments for ${current.title}`;
      } catch {
        finishEmbed?.(new Error('Comments could not load.'));
        mount.hidden = true;
        button.hidden = false;
        // Once initialized, recover with a full page reload: no second init or
        // reused global callback can race a delayed provider response.
        reloadRequired = initialized;
        button.textContent = reloadRequired ? 'Reload page' : 'Try again';
        status.textContent = reloadRequired
          ? 'Comments did not finish loading. Reload this page to try again.'
          : 'Comments could not load. Please try again.';
      } finally {
        button.disabled = false;
        if (select) select.disabled = false;
        section.removeAttribute('aria-busy');
      }
    });
  }

  const sections = document.querySelectorAll('[data-comments]');
  if (sections.length === 1) setup(sections[0]);
})();
