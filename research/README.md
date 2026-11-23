# The research

This folder holds the proof behind the rules. It keeps the method, the measured numbers and the sample sizes. The raw data and most study scripts are not included. Only `selection/candidates.py`, `hooks/hookcheck.py` and `hooks/features.py` ship, because the pipeline uses them.

## What these numbers are

- **Correlation, not cause.** These studies show what winners do. They do not prove why they won. Channel style, guest fame and timing all sit behind the numbers.
- **A study of about 5,200 YouTube Shorts on 54 podcast channels.** Filters gave 5,180 Shorts in one study and 5,236 in another. Most channels cover tech and business. About 30 Shorts were taken apart frame by frame.
- **Checked in late 2026.** Platforms change. Treat old numbers as a lead.
- **Multiple** means a Short's views divided by the median views of Shorts on that channel. **5x+** means five times the channel median or more. A "winner" is defined per study, usually 5x+ or 10x+.
- **Measured** means counted by code. **Judged** means read by a person or by Claude, which can be biased.

## If your niche is different

The findings on faces, sync, captions, length and layout are about how a Short plays, so they should carry across. The topic findings may not. In this study the saturated topic was AI: AI titles broke out least. Your saturated topic is yours. Set `show.topics` and `show.saturated_topic` in `brand/brand.json`. The rules use those values, not "AI".

## How to re-test in your own niche

You can repeat the study with public data. It costs some hours, not much money.

1. List 30 to 60 channels in your niche that post Shorts. Keep channels with 8 or more Shorts.
2. Pull each Short's title, length, date and views from public pages. Keep Shorts 3 to 90 days old.
3. Work out the multiple for each Short: views divided by that channel's median.
4. Sort titles into keyword buckets: your topics, household names, numbers, your saturated topic.
5. Compare the 5x+ rate per bucket. Then compare inside each channel, because big channels skew the totals.
6. Change a rule only when the result holds across all channels and inside most channels.

Also keep your own record. After 3 to 4 episodes, log each Short's score and its 7-day multiple, then see which tests predicted it. The Stats tab in the app gives you the views. Once you have 30 or more Shorts, your own data beats this study. If a rule fails on your channel, drop it and write down why.

## The files

- `selection/SELECTION.md`: which passage to pick.
- `hooks/HOOKS.md`: how it opens, spoken and written.
- `layout/LAYOUT.md`: the mix of frames.
- `LENGTH.md`: how long a Short can be.
- `captions/RESULT.md`: one line or two.
- `transitions/RESULT.md`: cuts or transitions.
- `deconstruct/FINDINGS.md`: the frame-by-frame study.
- `channels/REPORT.md`: which public channels to study.
- `descriptions/RESEARCH.md`: post copy on each platform.
