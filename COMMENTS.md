# Comments

Comments are prepared but disabled. The site does not contact Hyvor Talk until a visitor chooses **Show comments**. A GitHub Pages deployment needs no application server; Hyvor hosts the comments and moderation queue.

## Owner setup

1. Create a Hyvor account and add the atlas as a website in the [Hyvor Talk Console](https://talk.hyvor.com/). Choose a plan yourself. The current [pricing page](https://hyvor.com/talk/pricing) lists a 14-day trial and a Personal plan billed at €50 annually, with one website, one moderator and 2,500 credits per month. Each loaded comments component uses one credit; other features can use additional credits. Prices and limits may change.
2. In **Settings → Website → Allowed Domains**, add `khaihoanmath.github.io`. Add a custom domain separately if the site uses one. Do not permit every GitHub Pages site with a wildcard.
3. In **Settings → Embed → Configuration**, enable **site-wide pre-moderation for all comments**. Check the settings for each existing page too. All new comments and replies must wait for approval.
4. Keep the owner as the only moderator. Leave the **Trusted** user and IP lists empty. Remove every moderation rule whose action is **Publish**. Trusted users/IPs and automatic publication rules can bypass review.
5. Edited comments must also wait for approval. Hyvor documents this behavior when pre-moderation is enabled. Alternatively, disable author editing in **Settings → Comments → Editing**. Guest comments can only be edited by a moderator after publication.
6. Enable math in the editor. The integration also sets `editor.math` to `true`. Commenters type `$$` to start a KaTeX block. Images, GIFs and external media embeds are disabled here.
7. Review the [Hyvor privacy policy](https://hyvor.com/talk/privacy) and the notice beside the load button. Hyvor processes comment content and commenter information and uses authentication cookies/local storage. Guest names are required; guest email addresses are optional and visible to the site owner if supplied. IP collection is configurable. There are no advertising or tracking scripts in its embeds, according to its policy. Keep the site's privacy information consistent with the options actually enabled.
8. Find the **Website ID** under **Settings → Website**. This public numeric identifier belongs in the configuration. It is not an API secret. Never put Console API keys, account passwords, access tokens or SSO signing keys in this repository.

Do not enable the public integration until the moderation test below passes. Preparing these files does not create an account or buy a subscription.

## Verify moderation before release

Use an owner session, a separate ordinary commenter session, and an anonymous browser session. Run the test on a temporary preview restricted to the intended test domain, with the service settings already configured. If preview access is public, do not announce it as verified until these checks pass.

- Submit a new guest comment, a signed-in user's comment, and a reply. Each must appear in the owner's pending queue and remain invisible to the separate anonymous visitor before approval.
- Approve each as the owner. Confirm that it becomes visible only then. Submit another comment from the same identity to ensure there is no automatic trust exception.
- Edit an approved signed-in comment. Its new text must remain invisible until approved again. If editing is disabled, confirm that an ordinary commenter cannot edit it.
- Repeat on an article thread and two question threads. Confirm that comments stay with the selected thread, that titles are correct, and that links lead to the exact `#question-ID` anchor.
- Test a blocked or slow provider request and **Try again**. Failure must not expose an unmoderated alternative form.
- On a fresh page load, inspect the browser Network panel: there must be no Hyvor request before **Show comments**. Changing the selected discussion must not start a request.

`moderation_verified` is an editorial release gate. It does **not** enforce moderation on Hyvor's servers, and neither a hidden form nor a client-side check can provide that guarantee. Maintain the service-side settings after activation. Recheck them after changes to moderators, trusted users/IPs, rules or account configuration. If uncertain, disable comments and rebuild.

## Enable or disable

The committed configuration in `content/comments.json` is:

```json
{
  "enabled": false,
  "provider": "hyvor",
  "website_id": "",
  "moderation_verified": false
}
```

After completing the owner setup and moderation test, enter the Website ID as a decimal string and set both booleans to `true`. Rebuild and deploy through the normal workflow. To remove comments, set `enabled` to `false`, rebuild and deploy. Invalid settings stop the build rather than silently enabling comments.

## Build interface

`scripts/comments.mjs` exports:

```js
const config = await loadComments(repositoryRootURL);
const html = renderComments(config, {
  id: 'article:fekete',
  title: 'Fekete polynomials',
  url: 'https://khaihoanmath.github.io/polynomial-arithmetic-atlas/articles/fekete.html',
  threads: [{
    id: 'question:EXISTING_QUESTION_ID',
    title: 'Existing question title',
    url: 'https://khaihoanmath.github.io/polynomial-arithmetic-atlas/questions.html#question-EXISTING_QUESTION_ID',
    group: 'Questions'
  }]
});
```

Replace the example question placeholder with an existing lowercase question ID. Valid prefixes are `page:`, `article:` and `question:`. Never derive identity from a mutable title. Use the same question ID wherever it is discussed. Absolute HTTP(S) URLs are required; all choices must share the context URL's origin. Question URLs must use `#question-` followed by the bare ID.

`threads` is optional. When provided, the module renders a grouped selector and adds the context thread if absent. A `?thread=question%3Aexisting-id` parameter can select only a thread already present in the rendered options. It cannot create an arbitrary thread. The module renders one `#comments` section per page, or an empty string when disabled.

The parent build should include the local `assets/comments.css` stylesheet and deferred `assets/comments.js` script, and copy those assets, only when comments are enabled. Do not add a provider script, remote comment-count script, iframe, preconnect or provider component to the initial HTML. The client loads the official module only on an explicit button click, waits for its Web Component registration, and then loads the selected thread manually. The CSS matches the atlas and hides comment controls in print.

If a Content Security Policy is added, follow Hyvor's [security documentation](https://hyvor.com/talk/docs/security) for scripts, API/WebSocket connections, images and dynamically inserted styles. GitHub Pages does not supply an application backend for managing comment secrets; none are needed for this embed.

Run local checks with `node --test scripts/comments.test.mjs`. These checks cover configuration, escaping, thread URLs, request timing and retry races using a local mock. They do not certify a real Hyvor account's moderation configuration.

## Official documentation

- [HTML installation](https://hyvor.com/talk/docs/install-html)
- [Thread IDs, attributes, math settings and manual loading](https://hyvor.com/talk/docs/comments)
- [Embed loaded event](https://hyvor.com/talk/docs/comments-events)
- [Moderation and trusted users/IPs](https://hyvor.com/talk/docs/moderation)
- [Automatic moderation rules](https://hyvor.com/talk/docs/rules)
- [Author editing and re-moderation announcement](https://hyvor.community/t/hyvor-talk-console-api-updates-editing-options/77)
- [Commenting and KaTeX input](https://hyvor.com/talk/docs/commenting)
- [Allowed domains](https://hyvor.com/talk/docs/install-hubspot)

Documentation and prices checked on 12 November 2026. Live account setup and moderation testing remain to be completed by the owner before activation.

Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
