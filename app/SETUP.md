# Set up the app, step by step

You need about 30 minutes, a free Supabase account and a free Vercel account. Buffer comes last, and only when you want to post.

## 1. Make the brand files

Run `/shorts-setup` in the kit first. It writes `public/brand.css`, `public/brand.js`, `public/fonts/`, `public/img/` and `api/_brand.js`. The app does not start without them.

## 2. Create the Supabase project

1. Go to https://supabase.com and create a new project. Save the database password somewhere safe.
2. Wait until the project is ready.
3. Open SQL Editor, then New query.
4. Paste all of `schema.sql` and press Run. It creates the tables and a private bucket called `shorts-media`.
5. Check: Table Editor shows 7 tables that start with `shorts_`, and Storage shows `shorts-media`.

If `app.bucket` in brand.json is not `shorts-media`, change the last lines of `schema.sql` to match before you run it.

Supabase limits the size of one file. Check the limit under Storage settings. If an upload fails as too large, raise the limit or lower the file size.

## 3. Copy two Supabase values

Open Project Settings, then API. Copy:

- Project URL. This is `SUPABASE_URL`.
- The `service_role` secret key. This is `SUPABASE_SERVICE_KEY`.

The service key can read and change everything. Never paste it into a page, a chat or a public file.

## 4. Create the Vercel project

Run these from this folder. You need Node 20 or newer.

```bash
npm install
npm install -g vercel
vercel link
```

Answer yes to create a new project. When Vercel asks for settings, keep the defaults.

## 5. Set the environment variables

In Vercel, open your project, then Settings, then Environment Variables. Add each one for Production. `.env.example` lists them all.

| Name | Value | Needed |
|---|---|---|
| `SITE_USER` | The login name. Blank means `owner`. | No |
| `SITE_PASSWORD` | The login password. Pick a long one. | Yes |
| `SUPABASE_URL` | From step 3 | Yes |
| `SUPABASE_SERVICE_KEY` | From step 3 | Yes |
| `BUFFER_API_KEY` | From step 8 | To post |
| `BUFFER_CHANNELS` | From step 8 | To post |
| `POSTING_ENABLED` | Set to `1` only when you are ready | To post |
| `APIFY_TOKEN` | From https://apify.com. Costs money per run. | No |

With no `SITE_PASSWORD`, the app refuses every request. This is on purpose.

## 6. Deploy

```bash
vercel deploy --prod --yes
```

The last line it prints is your app's address. Run this command again after every change to the code or to the environment variables.

## 7. Check it

1. Open the address. The browser asks for a login. Enter your `SITE_USER` (or `owner`) and `SITE_PASSWORD`.
2. You see your logo and title, and four tabs with nothing in them yet. This is correct.
3. Open Stats. It says nothing is live yet. This is correct.

Put the address in `app.url` in brand.json, so the pipeline can publish to it.

## 8. Turn on posting (when you are ready)

Posting is off until step 4 below. Until then the app works for review, and it posts nothing.

1. In Buffer, connect your YouTube, Instagram and TikTok accounts.
2. On each channel, post one thing by hand in Buffer. The app checks Buffer's history before each booking, to stop double posts. If a channel has no history at all, the app refuses to book.
3. Create an API key at https://developers.buffer.com. This is `BUFFER_API_KEY`. Then get your channel ids. Replace `YOUR_API_KEY`, and in the second command `YOUR_ORG_ID` with the id from the first.

```bash
curl -X POST 'https://api.buffer.com' -H 'Content-Type: application/json' -H 'Authorization: Bearer YOUR_API_KEY' -d '{"query":"{ account { organizations { id name } } }"}'
curl -X POST 'https://api.buffer.com' -H 'Content-Type: application/json' -H 'Authorization: Bearer YOUR_API_KEY' -d '{"query":"{ channels(input: { organizationId: \"YOUR_ORG_ID\" }) { id name service } }"}'
```

Put the ids in `BUFFER_CHANNELS` as one line:

```json
{"youtube":{"id":"...","name":"My channel"},"instagram":{"id":"...","name":"my_handle"},"tiktok":{"id":"...","name":"my_handle"}}
```

Leave out a platform you do not use.

4. Set `POSTING_ENABLED` to `1` and deploy again.
5. Book one Short for a time a few hours away. Check it shows in Buffer with the right time. Cancel it in the app if you want, and check it leaves Buffer.

## If something is wrong

| You see | Why | Fix |
|---|---|---|
| `Not configured.` | No `SITE_PASSWORD` | Set it and deploy again |
| `Could not load` with a supabase error | Wrong URL or key, or `schema.sql` was not run | Check steps 2 and 3 |
| `Posting is off.` | `POSTING_ENABLED` is not `1` | Step 8 |
| `Buffer shows no posts on this channel` | The channel has no history | Post once by hand in Buffer |
| Instagram says not set up | No `APIFY_TOKEN` or no `posting.instagram_username` | Add both, or ignore it. The rest works. |
| No colours or a bare page | The brand files are missing | Step 1, then deploy again |
