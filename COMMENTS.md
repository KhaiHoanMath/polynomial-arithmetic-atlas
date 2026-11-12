# Comments

The atlas uses **GraphComment Basic** with the public site identifier `Polynomial-Arithmetic-Atlas`. The account is on the free Basic plan. This identifier is safe to include in the website; passwords and account tokens must never be committed.

## Review comments

Open the [site dashboard](https://graphcomment.com/admin/#/website/6af587de0d90fa8f5b1d455b/graphcomment), then choose **Moderation → Comments → Pending**. Review each submission and approve or reject it. Email notifications to the page manager are enabled.

Under **Settings → Graphcomment → Website settings**, keep **Pre-moderation** and **Pre-moderate all guest comments** enabled. Links are also pre-moderated, with the good-reputation exception unchecked. The owner is the sole administrator; no other moderators are assigned. AI moderation assistance is off.

Comments appear oldest first in a flat layout. Text formatting and links are allowed; media, image uploads, emoticons, and rewards are off.

## Checks completed — 12 November 2026

The real widget loaded in the site preview. The guest workflow was tested:

- A new comment entered the pending queue and was absent from a fresh anonymous view.
- Owner approval made it public.
- A second comment from the same guest remained pending; rejection kept it out of the public thread.
- A reply remained pending until owner approval, then appeared publicly.
- A fourth guest comment tested a separate question thread: it entered the pending queue and appeared after approval. A neighboring question remained empty, confirming that the discussions were separate.
- A real question-comment permalink was followed through the repaired routing to the correct discussion. No GraphComment iframe loaded before **Show comments**.
- All four test comments were moved to **Deleted**. The dashboard showed 0 pending, 0 approved, and 4 deleted comments.

The guest interface offered no author edit action. An ordinary signed-in account and edits to approved comments by registered users have **not** been tested. The saved site-wide pre-moderation setting and the exercised guest workflow support activation; they do not establish every behavior of GraphComment's service.

Follow up with a registered reader: test a new comment, a reply, a second submission after approval, and an edit to an approved comment. An edited contribution should require review before the changed text becomes public. If any tested posting route bypasses the intended approval policy, disable comments while correcting the provider settings or choosing another service. Public API and feed visibility have not been independently tested.

## Website configuration

`content/comments.json` controls the integration:

```json
{
  "enabled": true,
  "provider": "graphcomment",
  "shortname": "Polynomial-Arithmetic-Atlas",
  "moderation_verified": true
}
```

This is the active configuration. `moderation_verified` records the account-setting review and guest tests described above. It is not a security control, a claim that all posting methods were tested, or a guarantee of provider behavior. GraphComment's server settings enforce moderation.

To disable comments, set `enabled` to `false`, rebuild, and publish through the GitHub Pages workflow. Invalid configuration stops the build. Keep the moderation settings above after activation, and repeat the relevant checks after changing them.

## Threads and privacy

Each article uses a stable `article:ID`, each question a `question:ID`, and each general page a `page:ID`. The Comments page groups the discussions. Question links retain their exact `questions.html#question-ID` anchor. Changing a title or domain does not change a thread ID; never reuse an ID for a different topic.

Question comment permalinks and notifications are routed to the matching discussion in `comments.html`. The redirect accepts a known question-card anchor and one valid 24-digit hexadecimal `comment_id`, whether the provider puts it before or after the hash. Ordinary question links stay on the questions page. The redirect makes no GraphComment request; the reader still chooses **Show comments**.

The integration passes both `behaviour.uid` and the canonical `behaviour.url`, since GraphComment strips query strings when inferring thread identity. It uses the official `gc_graphlogin.js` loader and `__semio__gc_graphlogin` initializer.

No GraphComment script or iframe loads until the reader clicks **Show comments**. A notice links to the [reader privacy policy](https://www.graphcomment.com/en/commenter-privacy). The widget runs in an iframe and does not inherit the atlas's KaTeX renderer; native LaTeX support has not been verified.

The build publishes comment controls and their local assets only while enabled. It does not include this guide, the configuration file, editable sources, or withdrawn downloadable exports in the deployed site.

## Code checks

All 13 comment tests pass. The enabled preview passed the site check: 77 pages and 5,624 local links/assets. A separate HTML audit confirmed 184 unique discussion IDs, consistent mappings for all 53 articles, and valid links and anchors for all 107 questions. Each page has one comment section and no duplicate HTML IDs.

The tests cover configuration, escaping, thread selection, question permalink routing, loading on request, and failure recovery with a mock provider. They complement the live guest tests; they do not test GraphComment's server implementation.

After changes, run:

```sh
node --test scripts/comments.test.mjs
npm run build
npm run check
```

## Official sources

- [Basic plan and usage limits](https://www.graphcomment.com/en/products/graphcomment/pricing)
- [Pre-moderation](https://blog.graphcomment.com/en/freedom-of-expression-responsibility-and-moderation/)
- [Installation and stable thread IDs](https://developers.graphcomment.com/docs/getting-started)
- [Widget configuration](https://developers.graphcomment.com/docs/widget-configuration)
- [Reader privacy](https://www.graphcomment.com/en/commenter-privacy)
- [Data-processing terms](https://www.graphcomment.com/en/dpa)

Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
