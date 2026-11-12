# Comments

The atlas uses GraphComment Basic for discussions on articles, questions, and general pages. The integration is prepared but disabled until the owner supplies a site shortname and verifies moderation. Preparing these files does not create an account or enable posting.

## Owner setup

1. Open the [GraphComment back office](https://graphcomment.com/admin/) and sign in or create your own account. Add the atlas at `https://khaihoanmath.github.io/polynomial-arithmetic-atlas/`. Choose **Basic**. The [current plan](https://www.graphcomment.com/en/products/graphcomment/pricing) is free, without ads, up to 1,000,000 data loads per month. This is a usage limit, not a promise of unlimited hosting. No paid subscription is needed for this integration.
2. Select **Pre-moderation** for the whole site: the owner must approve each comment before publication. Do not select Post-moderation or Smart moderation; Smart moderation can approve established authors automatically. Inspect any per-page settings and automatic approval or trusted-user exceptions. Keep the owner as the only moderator if every approval must be yours.
3. Check how author edits are handled. The public documentation reviewed does not establish that edited approved comments return for review. Test this below. If edits bypass approval, disable author editing if GraphComment provides a server-side setting. Do not enable the integration if the required policy cannot be enforced.
4. Optional AI assistance is not owner approval. For a wholly manual review process, disable AI moderation. The [data-processing terms](https://www.graphcomment.com/en/dpa) document the option to disable it. Do not enable any automatic publication workflow.
5. Under the site's **Setup** tab, copy its public **shortname**, called `graphcommentId`. Store it as `shortname` in `content/comments.json`. It is an identifier, not a password. Never add account passwords, access tokens or API secrets to this repository.
6. Review the [reader privacy policy](https://www.graphcomment.com/en/commenter-privacy) and your account's privacy options. Readers see a notice before **Show comments** connects them to GraphComment. No GraphComment script or iframe loads before that click. We do not describe the service as cookie-free.

The exact dashboard location of the moderation controls must be checked in the owner's account. Public documentation confirms pre-moderation but does not establish every current menu label or exception.

## Verify before enabling

Use an owner session, an ordinary commenter session, and a separate anonymous viewing session. These tests require an actual owner-controlled GraphComment website.

- Submit an ordinary comment and a reply. Both must remain absent from the anonymous view and appear in the owner's pending queue.
- Approve them as owner and check that they then become visible. Submit another comment from the same reader to rule out automatic approval after the first accepted comment.
- Repeat with each enabled posting method, including guests if allowed.
- Edit an approved comment. The changed text must remain invisible until the owner approves it, or the service must prevent ordinary authors from editing it. Hiding an Edit button with CSS is not enforcement.
- Reject a pending comment and verify it never appears publicly. Keep all unapproved content out of public APIs and public comment feeds too.
- Test an article and two separate questions. Confirm that each thread is distinct and links point to the intended page or exact question anchor.
- Check that a fresh visit and a discussion selection make no GraphComment request before **Show comments**. Check a failed provider request and its retry control.
- Check keyboard navigation, narrow screens and ordinary mathematical discussion. Native LaTeX/KaTeX support has not been verified; the widget is in an iframe and does not inherit the atlas's KaTeX renderer. Do not promise math rendering without testing it.

`moderation_verified` records completion of these checks; it does not enforce GraphComment's server settings. Maintain those settings after activation. If they change or cease to meet the policy, disable comments and rebuild.

## Configuration

The committed configuration is disabled:

```json
{
  "enabled": false,
  "provider": "graphcomment",
  "shortname": "",
  "moderation_verified": false
}
```

Only after the live checks pass, enter the real shortname and set both booleans to `true`. Build and publish through the normal GitHub Pages workflow. To disable comments, set `enabled` to `false` and publish again. Invalid settings stop the build.

## Threads and loading

Each article has a stable `article:ID` thread, each question a `question:ID` thread, and each general page a `page:ID` thread. Questions link to `questions.html#question-ID`. The Comments page groups the available discussions; its query parameter can select only a known thread. Changing titles or the site domain does not change thread IDs.

GraphComment strips query strings when inferring a thread from a URL, so the integration always passes both `behaviour.uid` and `behaviour.url`. Never reuse an ID for an unrelated topic. The browser uses the official standard loader, `gc_graphlogin.js`, and the documented `__semio__gc_graphlogin` initializer. No account secret is needed in the browser.

The build publishes local comment assets and controls only while enabled. It never publishes this configuration file, source documentation, or private bibliography exports. Local tests exercise configuration, escaping, thread selection, lazy loading and failure handling with a mock provider. They do not prove real account moderation.

Run `node --test scripts/comments.test.mjs`, `npm run build`, and `npm run check` after changes.

## Official sources

- [Free plan and moderation features](https://www.graphcomment.com/en/products/graphcomment/pricing)
- [Definition of pre-moderation](https://blog.graphcomment.com/en/freedom-of-expression-responsibility-and-moderation/)
- [Installation and stable thread IDs](https://developers.graphcomment.com/docs/getting-started)
- [Widget configuration and events](https://developers.graphcomment.com/docs/widget-configuration)
- [Reader privacy](https://www.graphcomment.com/en/commenter-privacy)
- [Data-processing terms](https://www.graphcomment.com/en/dpa)

Documentation checked on 12 November 2026. Account setup and live moderation tests remain necessary before activation.

Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
