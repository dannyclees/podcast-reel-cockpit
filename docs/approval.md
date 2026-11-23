# How approval works

Nothing posts until you approve it. This page explains each status, from reading the app code (`app/api/act.js`, `app/api/post.js`, `app/public/app.js`).

The app sits behind a password on every page and every API route (`SITE_USER`, `SITE_PASSWORD`). If no password is set, the app refuses all visits. Real posting is off until `POSTING_ENABLED=1` in Vercel.

## The statuses

A Short has one overall status. It follows the platforms: if any platform is posted, it is **posted**. If not, and any platform is scheduled, it is **scheduled**. Otherwise it is **draft** or **approved**.

### Draft

- `publish.py` puts a Short here. You see the video, version tabs, music choice and a Feedback box.
- It has not been approved. The server refuses to schedule a draft.
- It shows in the **Drafts** tab.

### Approved

- You clicked Approve. If posting is on, one click approves and books the next free slot. The button shows the time.
- If posting is off, it only marks the Short approved. You can post by hand and record it in the app.
- The version on your screen is the one that gets booked. The button says so if you pick an older version.
- You can take back an approval while the Short is not scheduled or posted.

### Scheduled

- Buffer holds the post until its time. The Short is in the **Scheduled** tab with its time.
- **Move:** set a new time under Details. The app cancels the booking and books again.
- **Post now:** sends it at once. A waiting post is deleted first. If it cannot be deleted, nothing new is added.
- **Cancel:** see below.

The booked file is the full-quality master joined with your chosen music mix and SFX setting.

### Posted

- The app asks Buffer about waiting posts. A sent post becomes posted, with its live link. The Short moves to the **Live** tab.
- A posted Short cannot be cancelled from the app. Delete it on the platform itself.

### Failed (per platform)

- A platform can fail while the others are fine. The app shows the reason, like "that time has passed" or "post copy is empty", or the reason Buffer gave.
- Booking again retries only the platforms that are not booked.
- A post that vanishes from Buffer is marked failed.

## Notes

- Type in the **Feedback** box. The note is saved against that Short and the version on your screen. It stays **open** until someone marks it done.
- A Short with an open note also shows in the **Revisions** tab, oldest first. That holds even if it is booked or live, because the problem may already be public.
- Claude reads notes at the start of each `/shorts` run:
  ```bash
  python3 app-sync/pull.py
  python3 app-sync/feedback.py --open
  ```
- When a note is dealt with:
  ```bash
  python3 app-sync/feedback.py --done <id> --note "what was done"
  ```
- A general note should also become a rule with `/shorts-rule` (R19).

## Re-edits need a note (R125)

- Publishing a Short again makes a new version (round). Older versions stay playable.
- `publish.py` refuses round 2 and up without `--note`:
  ```bash
  python3 app-sync/publish.py <episode> <id> --note "what changed and why"
  ```
- The note shows under **Edits**, below the Feedback box, so you can track each version.
- A new round sets the status back to draft, unless the Short is already posted.
- **Careful:** publishing a new round does not remove a post already waiting in Buffer. Cancel the booking first, then publish, then approve again. Otherwise the old version can still go out.

## One booking per platform (R123)

Two requests must never book the same Short twice. The server has two guards. Both fail closed, so if a check cannot run, nothing is booked.

1. **Claim.** One atomic database write marks the platforms as "booking". A second request loses that write and is refused. A claim older than 10 minutes counts as a crash.
2. **Ask Buffer.** Before each create, the server asks Buffer if this exact text already sits on this channel. If so, it adopts that post and does not book again.

`repost: true` skips the second guard. Use it only for a post you deleted on purpose. There is no button for it.

Check for doubles at any time. This sends nothing, and it exits 1 if it finds any:

```bash
python3 app-sync/dupcheck.py
```

## Each Short gets its own time (R124)

- The app suggests the next free slot: `gap_hours` after the last booked post, never sooner than 20 minutes from now.
- The server decides the final time. If a time is within `clash_hours` of another Short, it moves to `gap_hours` after that Short and logs the move under the Short.
- Defaults are 1 h and 4 h. Both are under `posting` in `brand/brand.json`. Check that they are what you want before your first booking.
- A time must be more than 5 minutes ahead, or that platform fails with a reason.

## Holds

A hold stops a Short from being booked while you wait for something, like a fix or a date. It is a short text in the `hold` column of `shorts_items`.

- With a hold set, the app shows that text and "Waiting", and hides the Schedule button. The server refuses to book it and returns the hold text as the reason.
- There is no button to set a hold in the app. Ask Claude to set or clear it, or edit the row in Supabase.
- `app-sync/post_queue.py` is the exception. It books with force and clears the hold. Use it only when you want a fixed version booked as soon as it lands.

## Cancels

- **Cancel** removes the waiting post from Buffer on each platform and takes the Short back to approved.
- If Buffer says the post is already gone, that counts as cancelled. If the post is still there, the cancel fails and the app shows the error.
- A Short being booked right now cannot be cancelled. Try again in a minute.
- A post already live cannot be cancelled from here.

## The post queue (optional)

`python3 app-sync/post_queue.py` watches `app-sync/post_queue.json`. It waits for a named version to land, then approves and books it. If the version is not in the app 30 minutes before its slot, the slot moves 1 hour later. It runs only when you start it. An entry in that queue counts as your approval, so add only what you have already decided to post.

## What the system never does

- Post a draft.
- Post without `POSTING_ENABLED=1`.
- Book the same text twice on one channel, by the guards above.
- Delete anything already live.
