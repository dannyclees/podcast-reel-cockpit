#!/usr/bin/env python3
"""The approver's feedback from the app (the Feedback box in a Short's panel).

  python3 app-sync/feedback.py --open                 # list open feedback, oldest first
  python3 app-sync/feedback.py --all                  # open and done
  python3 app-sync/feedback.py --done 123 [--note "fixed in v5"]   # mark one done (several ids: --done 123 124)
  python3 app-sync/feedback.py --reopen 123

Each note is saved against the Short and the version (round) on screen at the time, with its time and state.
"""
import argparse, datetime, re, sys, urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sb import rest, brand  # noqa: E402

COLS = 'id,short_id,round_at,status_at,body,state,created_at,done_at,done_note'


def when(iso):
    tz = brand.timezone()
    return datetime.datetime.fromisoformat(iso).astimezone(tz).strftime(f'%a %d %b %H:%M {tz.key}')


def tab(v):
    """Same name as the app's version chips: "V4 B" = round 4, variant B."""
    m = re.search(r'\b([A-Z])$', (v.get('round_label') or '').split('·')[0].strip())
    return f"V{v['round']}" + (f" {m.group(1)}" if m else '')


def show(rows):
    if not rows:
        print('No feedback.')
        return
    titles = {i['id']: i['title'] for i in rest('shorts_items?select=id,title')}
    labels = {(v['short_id'], v['round']): tab(v) for v in rest('shorts_versions?select=short_id,round,round_label')}
    for f in rows:
        lab = labels.get((f['short_id'], f['round_at']), f"round {f['round_at']}")
        print(f"#{f['id']}  [{f['state']}]  {f['short_id']}  {lab} (round {f['round_at']})  {when(f['created_at'])}")
        print(f"    {titles.get(f['short_id'], '')}")
        for line in f['body'].splitlines():
            print(f"    > {line}")
        if f['state'] == 'done':
            print(f"    done {when(f['done_at'])}{': ' + f['done_note'] if f.get('done_note') else ''}")
        print()


def mark(ids, state, note=None):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for i in ids:
        body = {'state': state, 'done_at': now if state == 'done' else None, 'done_note': note if state == 'done' else None}
        r = rest(f'shorts_feedback?id=eq.{urllib.parse.quote(str(i))}&state=not.is.null', 'PATCH', body, prefer='return=representation')
        print(f"#{i}: {'marked ' + state if r else 'not found'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--open', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--done', nargs='+')
    ap.add_argument('--reopen', nargs='+')
    ap.add_argument('--note')
    a = ap.parse_args()
    if a.done:
        return mark(a.done, 'done', a.note)
    if a.reopen:
        return mark(a.reopen, 'open')
    flt = 'state=not.is.null' if a.all else 'state=eq.open'
    show(rest(f'shorts_feedback?select={COLS}&kind=eq.note&{flt}&order=created_at.asc&limit=500'))


if __name__ == '__main__':
    main()
