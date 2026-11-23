#!/usr/bin/env python3
"""Read the review app back into app-sync/state.json: status (Draft / Approved / Posted), chosen track,
per-platform state (scheduled / posted + link), SFX on/off and every feedback note. Run before re-rendering so the pipeline sees what was decided.

  python3 app-sync/pull.py            # writes app-sync/state.json and prints a short summary
"""
import datetime, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sb import rest, brand  # noqa: E402

OUT = Path(__file__).resolve().parent / 'state.json'


PLATFORMS = ('youtube', 'tiktok', 'instagram')
STAGGER = {'youtube': 0, 'tiktok': 15, 'instagram': 30}


def plan_of(ep, its):
    """The app's posting plan, resolved to clock times on the show's timezone. Same maths as planOf() in public/app.js. Plans only."""
    saved = ep.get('plan') or {}
    tz = brand.timezone()
    today = datetime.datetime.now(tz).date()
    nxt = datetime.date.fromisoformat(ep['recorded_on']) + datetime.timedelta(days=1) if ep.get('recorded_on') else today
    day = datetime.date.fromisoformat(saved['day']) if saved.get('day') else max(nxt, today)
    start, window_h, ov = saved.get('start', 8 * 60), saved.get('window_h', 20), saved.get('overrides') or {}
    approved = sorted([i for i in its if i['status'] != 'draft'], key=lambda i: i.get('num') or 99)
    gap = max(15, round(window_h * 60 / len(approved) / 15) * 15) if approved else 0
    def at(m):
        # aware + timedelta is wall-clock maths in Python, so 08:00 stays 08:00 across a clock change
        return (datetime.datetime.combine(day, datetime.time(0), tz) + datetime.timedelta(minutes=m)).isoformat()
    slots = {i['id']: {p: at(ov.get(i['id'], {}).get(p, start + j * gap + STAGGER[p])) for p in PLATFORMS} for j, i in enumerate(approved)}
    return {'day': day.isoformat(), 'start_min': start, 'window_h': window_h, 'gap_min': gap,
            'start_is_default': 'start' not in saved, 'slots': slots}


def main():
    eps = rest('shorts_episodes?select=*&order=recorded_on.desc')
    items = rest('shorts_items?select=*&order=episode_id.desc,num.asc')
    fb = rest('shorts_feedback?select=*&order=created_at.desc')
    state = {'pulled_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'episodes': {}, 'shorts': {}}
    for e in eps:
        state['episodes'][e['id']] = {'title': e['title'], 'recorded_on': e['recorded_on'],
                                      'plan': plan_of(e, [i for i in items if i['episode_id'] == e['id']]),
                                      'feedback': [f for f in fb if f['episode_id'] == e['id'] and not f['short_id']]}
    for it in items:
        state['shorts'][it['id']] = {
            'title': it['title'], 'round': it['round'], 'round_label': it['round_label'],
            'status': it['status'], 'approved': it['status'] in ('approved', 'scheduled', 'posted'),
            'track': it['track'], 'sfx': it.get('sfx', True), 'platforms': it['posted'],
            'feedback': [f for f in fb if f['short_id'] == it['id']],
        }
    OUT.write_text(json.dumps(state, indent=1, ensure_ascii=False))
    for sid, s in state['shorts'].items():
        notes = [f for f in s['feedback'] if f['kind'] == 'note']
        print(f"{sid:14} r{s['round']} {s['status']:9} track={s['track']:5} platforms={','.join(f"{k}:{v.get('state', 'posted')}" for k, v in s['platforms'].items()) or '-':34} notes={len(notes)}")
    print(f'Wrote {OUT}')


if __name__ == '__main__':
    main()
