# Auto-posting checklist: YouTube Shorts, TikTok, Instagram Reels

Last checked: 30 Oct 2026

How the app posts today: through Buffer (section 6). You connect your accounts to Buffer once. The app sends each post to Buffer with its time, and Buffer publishes it. Posting stays off until you set `POSTING_ENABLED=1`.

Before the first real post: post once by hand in Buffer on every channel you connect. Before each booking, the app asks Buffer whether that post already exists. If Buffer shows no posts at all on a channel, the app refuses to book, because it cannot rule out a double post.

What the rest of this page is: the facts you need if you ever want the app to post straight to each platform, without Buffer. Official docs only. Every claim has a link. Where a doc was unclear, it says "not confirmed".

The files this system makes: 9:16, H.264, about 30 to 90 s. These fit all three platforms (see the spec tables).

---

## 1. YouTube Shorts (YouTube Data API v3, `videos.insert`)

### 1.1 What must exist

| Item | Detail | Source |
|---|---|---|
| Google Cloud project | With YouTube Data API v3 turned on. Quota is set per project. | [Getting started](https://developers.google.com/youtube/v3/getting-started) |
| OAuth scope | Any one of: `https://www.googleapis.com/auth/youtube.upload`, `.../auth/youtube`, `.../auth/youtubepartner`, `.../auth/youtube.force-ssl`. Use `youtube.upload` (smallest). | [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert), [Scopes](https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps) |
| Quota | Default: 100 `videos.insert` calls per day, in their own "Video Uploads" bucket. Each upload costs 1 unit there. All other calls share 10,000 units per day. | [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert), [Getting started](https://developers.google.com/youtube/v3/getting-started), [Revision history, 1 Jun 2026](https://developers.google.com/youtube/v3/revision_history) |
| Compliance audit | Only needed if you want MORE quota than the default. | [Quota and Compliance Audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits) |
| Unverified project uploads | Today's reference says: "Videos uploaded from unverified API projects are not restricted to private viewing mode." An older note (21 Jul 2020) said uploads from unverified projects made after 28 July 2020 are locked to private until an audit. The current reference page is newer, so it should win. Not confirmed in practice: test with one upload. | [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert), [Revision history](https://developers.google.com/youtube/v3/revision_history) |
| Google app verification | Not needed for a personal-use app with fewer than 100 users. Users click through an "unverified app" warning. | [Google: exceptions to verification](https://support.google.com/cloud/answer/13464323) |
| Token trap | If the OAuth consent screen stays in "Testing", the refresh token expires in 7 days. You would have to sign in again every week. | [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2) |
| Channel per-day upload cap | Not confirmed. No number found in the API docs. | n/a |

### 1.2 File specs

| Spec | Value | Source |
|---|---|---|
| What makes it a Short | Square or vertical, up to 3 minutes long (uploads on or after 15 Oct 2024). 16:9 is not a Short. | [YouTube Help: Shorts length](https://support.google.com/youtube/answer/15424877) |
| Container | MP4, no edit lists, moov atom at the front (Fast Start) | [Upload encoding settings](https://support.google.com/youtube/answer/1722171) |
| Video codec | H.264, High Profile, progressive, 4:2:0 | [Upload encoding settings](https://support.google.com/youtube/answer/1722171) |
| Audio | AAC-LC or Opus, 48 kHz, stereo | [Upload encoding settings](https://support.google.com/youtube/answer/1722171) |
| Frame rate | Same as recorded | [Upload encoding settings](https://support.google.com/youtube/answer/1722171) |
| Max file size | 256 GB | [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert) |
| Min duration | Not confirmed | n/a |

### 1.3 Text limits

| Field | Limit | Source |
|---|---|---|
| Title | 100 characters. No `<` or `>`. | [videos resource](https://developers.google.com/youtube/v3/docs/videos) |
| Description | 5000 bytes (bytes, not characters). No `<` or `>`. | [videos resource](https://developers.google.com/youtube/v3/docs/videos) |
| Tags | 500 characters in total. Commas count. Tags with spaces count 2 extra (quotes). | [videos resource](https://developers.google.com/youtube/v3/docs/videos) |
| Hashtags | Put in title or description. More than 60 and YouTube ignores all of them. Up to 3 show by the title. | [YouTube Help: hashtags](https://support.google.com/youtube/answer/6390658) |

### 1.4 Scheduling

Yes, built in. Upload with `status.privacyStatus = private` and set `status.publishAt`. YouTube makes it public at that time. Rules:
- `publishAt` only works if the video is private and has never been published.
- A time in the past publishes it right away.

Source: [videos resource, status.publishAt](https://developers.google.com/youtube/v3/docs/videos)

Also set `status.selfDeclaredMadeForKids` and, if needed, `status.containsSyntheticMedia` on upload. Source: [videos resource](https://developers.google.com/youtube/v3/docs/videos)

### 1.5 What you must do yourself

1. Sign in to Google Cloud Console. Create a project. Turn on YouTube Data API v3.
2. Set up the OAuth consent screen. Set it to "In production" (not "Testing") so the token lasts past 7 days ([OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)). Keep it personal use, under 100 users ([verification exceptions](https://support.google.com/cloud/answer/13464323)).
3. Create a Web OAuth client ID. Add the app's redirect URL.
4. Open the app's "Connect YouTube" link once. Pick your channel. Click through the "unverified app" screen. Approve `youtube.upload`.

### 1.6 What the app can then do

- Store the refresh token in Supabase (server side only).
- Upload each approved Short with title, description, hashtags, made-for-kids flag.
- Schedule it with `publishAt`, or post now.
- Save the returned video ID and set the row to Scheduled or Posted.
- Up to 100 uploads a day on default quota.

---

## 2. TikTok (Content Posting API)

Two ways in:
- **Direct Post**: the app posts straight to the profile. Scope `video.publish`.
- **Upload (inbox)**: the app sends the video to your TikTok inbox. You finish and post in the TikTok app. Scope `video.upload`.

### 2.1 What must exist

| Item | Detail | Source |
|---|---|---|
| Developer app | Registered on TikTok for Developers, with the Content Posting API product added. For Direct Post, turn on the "Direct Post" setting. | [Get started: Direct Post](https://developers.tiktok.com/doc/content-posting-api-get-started) |
| Scopes | Direct Post: `video.publish`. Upload: `video.upload`. The app must be approved for the scope, and the user must authorise it. | [Direct Post ref](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post), [Get started: Upload](https://developers.tiktok.com/doc/content-posting-api-get-started-upload-content) |
| App review | Needs a real website (not a login page), visible Terms and Privacy Policy, a demo video of the full flow, icon, description. **Big blocker: "Apps must not be for private or personal use."** Review time not stated. | [App review guidelines](https://developers.tiktok.com/doc/app-review-guidelines) |
| Audit (Direct Post) | Without an audit, every post is private (SELF_ONLY). Unaudited clients can only post to a private account. Max 5 users posting per 24 h. | [Get started: Direct Post](https://developers.tiktok.com/doc/content-posting-api-get-started), [Direct Post ref](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post), [Content Sharing Guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines) |
| Audit (Upload/inbox) | Not confirmed. The Upload docs do not mention an audit. | [Get started: Upload](https://developers.tiktok.com/doc/content-posting-api-get-started-upload-content) |
| Sandbox | Up to 5 sandboxes, up to 10 target accounts you own. No Content Posting API for public videos. | [Add a sandbox](https://developers.tiktok.com/doc/add-a-sandbox) |
| Posts per day | "Typically around 15 posts per day" per creator, shared by all API clients. No fixed number in the API ref. Error `spam_risk_too_many_posts` when hit. | [Content Sharing Guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines), [Creator info ref](https://developers.tiktok.com/doc/content-posting-api-reference-query-creator-info) |
| Inbox cap | At most 5 pending shares in any 24 h. | [Upload ref](https://developers.tiktok.com/doc/content-posting-api-reference-upload-video) |
| Rate limits | Post init and upload init: 6 requests per minute per user token. Creator info: 20 per minute. | [Direct Post ref](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post), [Upload ref](https://developers.tiktok.com/doc/content-posting-api-reference-upload-video), [Creator info ref](https://developers.tiktok.com/doc/content-posting-api-reference-query-creator-info) |
| Tokens | Access token: 24 hours. Refresh token: 365 days. | [Token management](https://developers.tiktok.com/doc/oauth-user-access-token-management) |
| Account type | No Business account needed in the docs read. Not confirmed either way. | n/a |

### 2.2 File specs

| Spec | Value | Source |
|---|---|---|
| Format | MP4 (recommended), WebM, MOV | [Media transfer guide](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide) |
| Codec | H.264 (recommended), H.265, VP8, VP9 | [Media transfer guide](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide) |
| Size | Max 4 GB | [Media transfer guide](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide) |
| Duration | API max 10 minutes. Per-creator max is in `max_video_post_duration_sec`. Min not confirmed. | [Media transfer guide](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide), [Creator info ref](https://developers.tiktok.com/doc/content-posting-api-reference-query-creator-info) |
| Resolution | 360 to 4096 px each side | [Media transfer guide](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide) |
| Frame rate | 23 to 60 FPS | [Media transfer guide](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide) |
| Aspect ratio | Not confirmed (not stated on the spec page) | n/a |
| Upload chunks | 5 MB to 64 MB each (last up to 128 MB). Under 5 MB: send whole. | [Media transfer guide](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide) |
| Pull from URL | URL domain or prefix must be verified in the developer portal, https, no redirect | [Media transfer guide](https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide) |

### 2.3 Text limits

| Field | Limit | Source |
|---|---|---|
| Title (caption, Direct Post) | 2200 UTF-16 runes. Hashtags go in here. | [Direct Post ref](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post) |
| Hashtag count | Not confirmed | n/a |
| Caption (Upload/inbox) | Not documented for video. You type it in the TikTok app. | [Get started: Upload](https://developers.tiktok.com/doc/content-posting-api-get-started-upload-content) |

### 2.4 Scheduling

No. The Direct Post API has no publish-time field ([Direct Post ref](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post)). The app needs its own scheduler that calls the API at the right time (see "Scheduler" below).

Catch: TikTok's rules expect a person on each post. The post screen must show your TikTok display name, a privacy dropdown with no default, Comment/Duet/Stitch off by default, a commercial content toggle, a consent line, and a preview. The app must not send content until the user clearly agrees. ([Content Sharing Guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines)). Whether "you approve now, app posts later" passes the audit: not confirmed.

### 2.5 What you must do yourself

1. Sign in to TikTok for Developers. Create the app. Add Login Kit and the Content Posting API. Turn on Direct Post.
2. Put up a real website page plus Terms and Privacy Policy pages.
3. Record a demo video of the full posting flow.
4. Submit for app review. Expect the "not for private or personal use" rule to be a problem ([App review guidelines](https://developers.tiktok.com/doc/app-review-guidelines)).
5. Apply for the Direct Post audit, or posts stay private.
6. Connect his TikTok account once through the app and approve the scopes.

### 2.6 What the app can then do

- Before each post: call creator info, check he can post, check video length.
- Direct Post (after audit): send title and video, poll status, save the post ID, set the row to Posted.
- Upload (inbox): send the video. You get a notice in TikTok and tap to finish. Max 5 waiting at once per 24 h.
- Refresh the 24 h access token on its own for up to 365 days.

---

## 3. Instagram Reels (Instagram API with Instagram Login)

### 3.1 What must exist

| Item | Detail | Source |
|---|---|---|
| Account type | Instagram professional account (Business or Creator). Personal accounts are not covered. | [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview), [Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login) |
| Facebook Page | Not needed with Instagram Login. Needed only with the Facebook Login route. | [Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login), [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview) |
| Meta app | App type must be **Business**. Use case "Other". Add the Instagram product. | [Create an Instagram app](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app) |
| Scopes | `instagram_business_basic`, `instagram_business_content_publish` | [Content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/), [Business Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login) |
| Access level | Overview: Standard Access is "all your app needs" if it only serves your own accounts. Advanced Access (App Review plus Business Verification) is only for accounts you do not own. | [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview) |
| App Review / Business Verification | The "Create an app" page says App Review is required "before your app can access live data", and asks to connect a verified business. This clashes with the overview. Not confirmed which applies to an own-account, Standard Access app. | [Create an Instagram app](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app) |
| Tester account | The Instagram account added in the dashboard to make tokens "must be public". | [Create an Instagram app](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app) |
| Rate limit | 100 API-published posts per 24 h moving window. (Same page also says 50 in the carousel section. Not reconciled.) Check live with `GET /<IG_ID>/content_publishing_limit`. | [Content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/) |
| Tokens | Long-lived token lasts 60 days. Refresh it once it is at least 24 h old, before it expires. | [Business Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login) |
| Video hosting | The video must sit at a public URL when you publish. Meta fetches it. | [Content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/) |

### 3.2 File specs (Reels)

| Spec | Value | Source |
|---|---|---|
| Container | MOV or MP4, no edit lists, moov atom at front | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Video codec | H.264 or HEVC, progressive, closed GOP, 4:2:0 | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Audio | AAC, 48 kHz max, mono or stereo, 128 kbps | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Frame rate | 23 to 60 FPS | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Width | Max 1920 px | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Aspect ratio | 0.01:1 to 10:1 allowed. 9:16 recommended. | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Duration | 3 s min, 15 min max | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Size | 300 MB max | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Bitrate | VBR, 25 Mbps max | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Cover | `cover_url` (JPEG, 8 MB max, 9:16 advised) or `thumb_offset` in ms | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |

### 3.3 Text limits

| Field | Limit | Source |
|---|---|---|
| Caption | 2200 characters | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Hashtags | 30 max | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| @ tags | 20 max | [IG User Media ref](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |

### 3.4 How a Reel is posted

1. `POST /<IG_ID>/media` with `media_type=REELS` and `video_url`. Returns a container ID.
2. Check `GET /<CONTAINER_ID>?fields=status_code` once a minute, for up to 5 minutes.
3. `POST /<IG_ID>/media_publish` with `creation_id`.
4. A container not published within 24 h expires.

Source: [Content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/). Note: `upload_type=resumable` is only for Facebook Login apps, so with Instagram Login use `video_url` (same page).

### 3.5 Scheduling

No publish-time field in the docs. The docs talk about apps that "allow app users to schedule posts", meaning the app does the waiting. The app needs its own scheduler. Source: [Content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/)

### 3.6 What you must do yourself

1. In the Instagram app: switch to a professional account (Creator or Business). Help page: [Set up a professional account](https://help.instagram.com/502981923235522). Instagram Help says a private account becomes public when switched. Not confirmed by direct read (the page needs JavaScript).
2. Sign in to Meta for Developers. Create a Business type app. Add the Instagram product ([Create an Instagram app](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app)).
3. Add his Instagram account in "API setup with Instagram login" and log in to it.
4. If Meta asks: connect a verified business and submit App Review with a screen recording. Not confirmed if needed for own-account use.
5. Approve the consent screen for `instagram_business_basic` and `instagram_business_content_publish`.

### 3.7 What the app can then do

- Make a public (or signed) link to the video in Supabase Storage.
- Create the container, wait for FINISHED, publish.
- Check `content_publishing_limit` first.
- Refresh the 60-day token on a timer.
- Save the media ID, set the row to Posted.

---

## 4. The scheduler (needed for TikTok and Instagram)

Only YouTube can schedule inside the API. For the other two, the app must fire the post itself.

| Option | Limit | Source |
|---|---|---|
| Vercel Cron, Hobby plan | Once per day only. Fires anywhere in the hour (±59 min). | [Vercel cron pricing](https://vercel.com/docs/cron-jobs/usage-and-pricing) |
| Vercel Cron, Pro plan | Once per minute, per-minute precision | [Vercel cron pricing](https://vercel.com/docs/cron-jobs/usage-and-pricing) |
| Supabase Cron | Every second to once a year. Can call an HTTP endpoint or Edge Function. | [Supabase Cron](https://supabase.com/docs/guides/cron) |

Plan: a `scheduled_posts` row per Short per platform with a time. A cron job every few minutes picks rows that are due and posts them. Supabase Cron avoids the Vercel Hobby once-a-day limit.

---

## 5. Order of work

1. **YouTube first.** No app review for personal use. Scheduling is built in. 100 uploads a day free. Main risk: the private-lock question for unverified projects. Test with one upload.
2. **Instagram second.** Switch to Creator, make a Business type Meta app, Standard Access may be enough for your own account. Needs a public video link and a scheduler of your own. Risk: the App Review clash in Meta's docs.
3. **TikTok last.** Needs app review and an audit. The review rules say personal-use apps are rejected. Until audited, posts are private only. Fallback: Upload (inbox) mode, where you tap "post" in TikTok yourself (max 5 waiting per 24 h).

---

## 6. Cheaper shortcut

A third-party scheduler can do the three platform reviews for you. You connect your accounts to it once, and the app calls its one API.

| Tool | What its docs confirm | Source |
|---|---|---|
| Buffer | Public API on every plan, including Free (1 API key, 1,000 requests per channel per 30 days, up to 3,000). Lists Instagram, TikTok and YouTube. Exact-time scheduling with `customScheduled` and `dueAt`. Note: the scheduling guide's platform list leaves out TikTok, the Help Center includes it. | [Buffer Help: API](https://support.buffer.com/en-us/articles/using-buffers-api-GtIYIQilz5), [Posts and scheduling](https://developers.buffer.com/guides/posts-and-scheduling.html) |
| Metricool | API only on Advanced and Custom plans. Its MCP connector works on any plan. Whether its API covers TikTok, Shorts and Reels: not confirmed. | [Metricool plans and API](https://help.metricool.com/plans-add-ons-and-api-access-explained-xux1u) |
| Later | No public developer API found in its official help docs. Not confirmed. | [Later Help Center](https://help.later.com/hc/en-us) |

Trade-off: one connection and no app reviews, but you live inside that tool's limits and rules. Test on the free tier before paying for anything.

---

## 7. The posting plan (built into the app)

The app plans the times. A plan posts nothing by itself. Nothing reaches any account until you turn posting on and book a Short.

How it works:

- It takes the approved Shorts of one episode and spreads them over a window. The default window is 20 hours.
- 5 Shorts post one every 4 h. 10 Shorts post one every 2 h. The gap is rounded to 15 minutes.
- The default start is 08:00 in your show time zone (`posting.timezone` in brand.json), on the day after recording (or today, if that day has passed).
- Why a default: the YouTube Analytics API has no hour-of-day data. Its only time dimensions are `day` and `month` ([YouTube Analytics dimensions](https://developers.google.com/youtube/analytics/dimensions)). The "when your viewers are on YouTube" chart is in YouTube Studio only. If Studio shows a better hour, set the start by hand.
- Each platform has its own lane. TikTok goes 15 min after YouTube. Instagram goes 30 min after YouTube.
- You can change the day, the start time and the window (12, 16, 20 or 24 h). You can drag a slot, or click it and press the arrow keys (15 min, Shift for 1 h). "Undo nudges" puts the slots back on the even spread.
- The plan is saved in `shorts_episodes.plan` (Supabase). `app-sync/pull.py` writes the exact times per Short per platform into `state.json`, under `episodes.<id>.plan.slots`.

How it plugs into auto-posting later:

- YouTube: upload each Short as `private` with `publishAt` set to its YouTube slot (see 1.4). YouTube publishes it at that time.
- TikTok and Instagram: the cron job in section 4 reads the slots and posts each one when it is due.
