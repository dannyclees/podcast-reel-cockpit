-- Full database setup for the Shorts review app.
-- Paste this into the Supabase SQL editor and press Run, once. Running it again changes nothing.
-- The app talks to the database from the server with the service key. The browser never sees the database.
-- So row level security is ON with no policies: only the service key can read or write.

create table if not exists shorts_episodes (
  id text primary key,
  title text not null,
  recorded_on date,
  created_at timestamptz not null default now(),
  full_url text,
  plan jsonb,
  full_url_auto boolean not null default false,
  full_title text
);

create table if not exists shorts_items (
  id text primary key,
  episode_id text not null references shorts_episodes (id) on delete cascade,
  num int,
  title text not null,
  round int not null default 1,
  round_label text,
  status text not null default 'draft' check (status in ('draft', 'approved', 'scheduled', 'posted')),
  track text not null default 'none',
  posted jsonb not null default '{}',
  copy jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  sfx boolean not null default true,
  hold text
);

create table if not exists shorts_versions (
  id bigint generated always as identity primary key,
  short_id text not null references shorts_items (id) on delete cascade,
  round int not null,
  round_label text,
  change_note text,
  video_path text not null,
  poster_path text,
  tracks jsonb not null default '{}',
  duration real,
  created_at timestamptz not null default now(),
  master_path text,
  play jsonb not null default '{}',
  unique (short_id, round)
);

create table if not exists shorts_feedback (
  id bigint generated always as identity primary key,
  episode_id text not null references shorts_episodes (id) on delete cascade,
  short_id text references shorts_items (id) on delete cascade,
  kind text not null default 'note' check (kind in ('note', 'change', 'status')),
  author text not null default 'owner',
  body text not null,
  status_at text,
  round_at int,
  track_at text,
  created_at timestamptz not null default now(),
  state text check (state in ('open', 'done')),
  done_at timestamptz,
  done_note text
);

create table if not exists shorts_kv (
  k text primary key,
  v jsonb not null default '{}',
  updated_at timestamptz not null default now()
);

create table if not exists shorts_stats (
  id bigserial primary key,
  short_id text not null references shorts_items (id) on delete cascade,
  platform text not null check (platform in ('youtube', 'tiktok', 'instagram')),
  at timestamptz not null default now(),
  views bigint,
  likes bigint,
  comments bigint,
  shares bigint,
  source text not null
);

create table if not exists shorts_trace (
  id bigserial primary key,
  at timestamptz not null default now(),
  trace_id text,
  ua text,
  build text,
  layout text,
  age_min int,
  events jsonb not null default '[]'
);

create index if not exists shorts_items_episode on shorts_items (episode_id);
create index if not exists shorts_versions_short_round on shorts_versions (short_id, round desc);
create index if not exists shorts_feedback_created on shorts_feedback (created_at desc);
create index if not exists shorts_feedback_short on shorts_feedback (short_id);
create index if not exists shorts_feedback_open on shorts_feedback (created_at desc) where state = 'open';
create index if not exists shorts_stats_short_platform_at on shorts_stats (short_id, platform, at desc);
create index if not exists shorts_stats_at on shorts_stats (at desc);
create index if not exists shorts_trace_at on shorts_trace (at desc);

alter table shorts_episodes enable row level security;
alter table shorts_items enable row level security;
alter table shorts_versions enable row level security;
alter table shorts_feedback enable row level security;
alter table shorts_kv enable row level security;
alter table shorts_stats enable row level security;
alter table shorts_trace enable row level security;

-- The service key must be able to reach these tables, also on projects that no longer grant this by default.
grant select, insert, update, delete on
  shorts_episodes, shorts_items, shorts_versions, shorts_feedback, shorts_kv, shorts_stats, shorts_trace
  to service_role;
grant usage, select on sequence shorts_stats_id_seq, shorts_trace_id_seq to service_role;

-- Private bucket for the videos. If brand.json sets a different app.bucket, change the name here too.
insert into storage.buckets (id, name, public) values ('shorts-media', 'shorts-media', false)
  on conflict (id) do nothing;
