// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
(() => {
  'use strict';
  const moduleURL = 'https://talk.hyvor.com/embed/embed.js';
  const componentName = 'hyvor-talk-comments';
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
    if (!window.customElements) return Promise.reject(new Error('Web Components are unavailable.'));
    if (customElements.get(componentName)) return Promise.resolve();
    if (!providerReady) {
      providerReady = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = moduleURL;
        script.type = 'module';
        script.async = true;
        script.dataset.commentsProvider = 'hyvor';
        script.addEventListener('error', () => {
          script.remove();
          providerReady = undefined;
          reject(new Error('Comments script could not load.'));
        }, { once: true });
        customElements.whenDefined(componentName).then(resolve, reject);
        document.head.appendChild(script);
      });
    }
    // A timeout does not insert another script: a slow request can still finish.
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
    const websiteId = section.dataset.websiteId;
    let current;
    const threads = new Map();
    try {
      if (!/^[1-9]\d*$/.test(websiteId) || section.dataset.moderationVerified !== 'true') {
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
      // URL parameters can only choose a thread already emitted by the build.
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

    let generation = 0;
    let cancelEmbed;
    function clearEmbed() {
      if (cancelEmbed) cancelEmbed();
      cancelEmbed = undefined;
      mount.replaceChildren();
      mount.hidden = true;
    }
    select?.addEventListener('change', () => {
      const next = threads.get(select.value);
      if (!next || next.id === current.id) return;
      generation += 1;
      current = next;
      clearEmbed();
      button.hidden = false;
      button.disabled = false;
      button.textContent = 'Show comments';
      status.textContent = '';
      section.removeAttribute('aria-busy');
    });

    button.addEventListener('click', async () => {
      if (button.disabled) return;
      const attempt = ++generation;
      const thread = current;
      button.disabled = true;
      if (select) select.disabled = true;
      section.setAttribute('aria-busy', 'true');
      status.textContent = 'Loading comments…';
      clearEmbed();
      try {
        await loadProvider();
        if (attempt !== generation) return;
        const embed = document.createElement(componentName);
        embed.setAttribute('website-id', websiteId);
        embed.setAttribute('page-id', thread.id);
        embed.setAttribute('page-url', thread.url);
        embed.setAttribute('page-title', thread.title);
        embed.setAttribute('loading', 'manual');
        embed.setAttribute('settings', JSON.stringify({
          editor: { math: true, images: false, gifs: false, embeds: false },
          top_widget: 'none'
        }));
        let stopThisEmbed;
        const ready = new Promise((resolve, reject) => {
          let settled = false;
          const finish = error => {
            if (settled) return;
            settled = true;
            clearTimeout(timer);
            embed.removeEventListener('loaded', loaded);
            if (cancelEmbed === stopThisEmbed) cancelEmbed = undefined;
            error ? reject(error) : resolve();
          };
          const loaded = () => finish();
          const timer = setTimeout(() => finish(new Error('Comments could not finish loading.')), timeoutMs);
          stopThisEmbed = () => finish(new Error('Comment thread changed.'));
          cancelEmbed = stopThisEmbed;
          embed.addEventListener('loaded', loaded, { once: true });
        });
        mount.replaceChildren(embed);
        try {
          // Listen before calling load(), including if the provider resolves immediately.
          const loading = embed.load();
          if (loading && typeof loading.catch === 'function') loading.catch(() => stopThisEmbed());
        } catch (error) {
          stopThisEmbed();
          await ready.catch(() => {});
          throw error;
        }
        await ready;
        if (attempt !== generation) return;
        mount.hidden = false;
        button.hidden = true;
        status.textContent = `Comments for ${thread.title}.`;
      } catch {
        if (attempt !== generation) return;
        clearEmbed();
        button.hidden = false;
        button.textContent = 'Try again';
        status.textContent = 'Comments could not load. Please try again.';
      } finally {
        if (attempt === generation) {
          button.disabled = false;
          if (select) select.disabled = false;
          section.removeAttribute('aria-busy');
        }
      }
    });
  }

  for (const section of document.querySelectorAll('[data-comments]')) setup(section);
})();
