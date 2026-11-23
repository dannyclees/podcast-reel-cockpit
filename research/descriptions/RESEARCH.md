# Post copy for podcast Shorts: what works

Checked in late 2026. Platforms change these rules, so check before you rely on one.

Tags: **[OFFICIAL]** = the platform's own words. **[MEASURED]** = pulled from real public accounts with yt-dlp. **[OPINION]** = marketing blogs. Treat opinion as a guide, not a law.

## What top podcast accounts do [MEASURED]

Pulled from the public YouTube Shorts tab and TikTok feed of each account. These are public shows, named because they are the data.

- Diary of a CEO, YouTube Shorts: ALL CAPS label titles, e.g. "ZELENSKYY OPENS UP ABOUT THE WAR" (815K views), "HOW TO MAKE YOUR FIRST MILLION" (305K).
- Diary of a CEO description: the first line is a question, or a two-beat story ("At 12... At 41..."). 0 hashtags. About 2,000 characters.
- All-In, YouTube Shorts: title = "Speaker: claim". Description = follow links, then 3 hashtags (1 branded + 2 broad).
- All-In, TikTok: caption = the same "Speaker: claim" title, then a long word-for-word quote. It is rich in keywords and searchable.
- TBPN: short label titles, e.g. "Jay Leno: "The Middle Class Is Dead"" (88K). TikTok captions are 2 to 4 words. Description = newsletter + links, 0 hashtags.
- Hard Fork: the title is a question. The description opens by repeating the question, then 2 lines of context.
- Modern Wisdom: first line = "Watch the full episode here" with a link. 0 hashtags.
- Lex Fridman clips: "Name on topic", e.g. "Elon Musk on Israel-Palestine" (1M). Description = one line, the full-episode link.
- Emoji: rare. Most posts have none.
- Pattern: none of these accounts use hashtag walls. 0 to 3 on YouTube.
- Gap: Instagram captions could not be pulled (login wall). The Instagram rules below come from official and blog sources only.

## YouTube Shorts

- Up to 3 hashtags from the description show next to the title. [OFFICIAL] https://support.google.com/youtube/answer/6390658
- Over 60 hashtags and YouTube ignores all of them. Too many tags can get a video pulled from search. [OFFICIAL] same page
- Hashtags must match the video. Unrelated tags can get it removed. [OFFICIAL] same page
- Title max 100 characters. Only about 40 to 60 show in the feed, so the topic goes first. [OPINION] https://hashtagtools.io/blog/youtube-shorts-character-limits-title-description-hashtags-2026
- About 157 characters of description show before "more". Put the fact in line 1. [OPINION] same source
- Links in Shorts descriptions are not clickable (since 31 Aug 2023). Use the "Related video" field to link the full episode. [OFFICIAL, quoted via] https://tubefilter.com/2023/08/10/youtube-shorts-comments-spam/ and https://support.vevo.com/hc/en-us/articles/53791074157083-YouTube-Shorts
- Still put the full-episode link in the description. Modern Wisdom and Lex do. It works on desktop and in search. [MEASURED]
- Title glance test: name + topic, or a plain claim. "Speaker: claim" and "Name on topic" are the most readable. [MEASURED]

## TikTok

- TikTok ranks with "video information" like captions, sounds and hashtags. [OFFICIAL, 2020 newsroom post, archived] https://thebrandberries.com/tiktok-reveals-how-it-recommends-foryou-videos/
- Caption keywords count for TikTok search. Write the words people type. [OPINION] https://metricool.com/tiktok-seo/
- Keywords early in the caption count more (some say the first 100 characters). No official source for the 100. [OPINION] https://www.capcut.com/create/tiktok-caption-keywords-discoverability
- About 80 to 100 characters show before "more". Sources disagree. [OPINION] https://www.clipspeed.ai/blog/instagram-reels-captions.html
- 3 to 5 specific hashtags beat 20 generic ones. [OPINION] https://virlo.ai/blog/tiktok-seo-how-do-i-rank-videos-in-tiktok-search-2026
- Caption links are not clickable. Send people to the link in bio. [OPINION, consistent] https://social.colostate.edu/best-practices/how-to-add-a-link-to-a-tiktok-post-and-why-its-not-like-other-platforms/
- Max caption length: 2,200 or 4,000 characters. Sources disagree. Short wins in practice. [MEASURED + OPINION]

## Instagram Reels

- Hard cap: 5 hashtags per post or Reel, from Dec 2025. Comments count toward the 5. [OFFICIAL, quoted via] https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/
- Instagram says "fewer (up to 5) more targeted hashtags" work better than generic ones. [OFFICIAL, same]
- Instagram's head says hashtags do not raise reach. They tell people what the post is about. [OFFICIAL, quoted via same]
- Caption words are indexed for search. Keywords go in the caption, not comments. [OPINION, cites Instagram guidance] https://www.truefuturemedia.com/articles/instagram-reach-2026-algorithm-reels-carousels-caption-seo
- About 125 characters show before "more". Not official, sometimes less. [OPINION] https://www.clipspeed.ai/blog/instagram-reels-captions.html
- Total caption max 2,200 characters. [OPINION, consistent] https://www.sendible.com/insights/instagram-character-limit
- Caption links are not clickable. Use the link in bio. [OPINION, consistent] https://www.inro.social/blog/meta-verified-clickable-links

## First-line patterns to use

1. **News fact + source:** the verified fact in plain words, outlet and date.
2. **Two-beat contrast:** two short facts side by side.
3. **Speaker: claim:** who says it, then the claim.
4. **Question:** a real question the clip answers.

## Rules for every post

- Line 1 is the topic in words people search. Under 100 characters (TikTok), under 125 (Instagram), under about 150 (YouTube).
- Facts only, with outlet and date when it is news. Opinions are named as the host's view.
- Hashtags: YouTube 3, TikTok 4 to 5, Instagram 5 max. 1 branded (from `show.handle`) + topic tags. `posting.always_tags` are added for you.
- Link: the YouTube description gets the full-episode link (also set it as the Related video). TikTok and Instagram say "full episode, link in bio".
- No emoji. Top accounts use them rarely, so leaving them out costs nothing.

## Where post copy goes

Write `research/descriptions/<episode>.json`, one key per Short id. Each holds `youtube_title`, `youtube_description`, `tiktok_caption`, `instagram_caption` and an optional `hashtags` list. `publish.py` reads this file and sends it to the app. Read every piece against the rules above and against `show.voice` and `show.banned_words`, then fix anything that sounds machine-written.
