#!/usr/bin/env python3
"""Validate and render HAYVN's daily reflection. No network or paid APIs."""
import argparse
import datetime as dt
import difflib
import html
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

START = '<!-- HEALING_REFLECTION_START -->'
END = '<!-- HEALING_REFLECTION_END -->'
FONT = 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,500&family=Lora:ital,wght@0,400;0,500;1,400&family=Cinzel:wght@400;500&display=swap'


def today():
    return dt.datetime.now(ZoneInfo('America/Toronto')).date().isoformat()


def words(text):
    return re.findall(r"\b[\w]+(?:[’'\-][\w]+)*\b", text)


def validate(note, archive):
    date = note.get('date', '')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
        raise ValueError('Publication date must be YYYY-MM-DD')
    dt.date.fromisoformat(date)
    for key in ['headline', 'theme', 'intention']:
        if not isinstance(note.get(key), str) or not note[key].strip():
            raise ValueError(f'Missing {key}')
    if len(note['headline']) > 150 or len(note['theme']) > 70:
        raise ValueError('Headline or theme too long')
    paragraphs = note.get('paragraphs')
    if not isinstance(paragraphs, list) or not 5 <= len(paragraphs) <= 12:
        raise ValueError('Expected 5–12 prose paragraphs')
    if any(not isinstance(p, str) or not p.strip() for p in paragraphs):
        raise ValueError('Empty paragraph')
    text = '\n'.join(paragraphs)
    if not 500 <= len(words(text)) <= 600:
        raise ValueError(f'Expected 500–600 words; got {len(words(text))}')
    all_text = ' '.join([note['headline'], text, note['intention'], note['theme']])
    if re.search(r'[<>]|https?://', all_text):
        raise ValueError('Use plain prose without HTML or external links')
    forbidden = r'\b(unlock your potential|best version of yourself|in today.s fast.paced world|raise your vibration|cure your|heal your trauma|guaranteed healing|as an AI)\b'
    if re.search(forbidden, all_text, re.I):
        raise ValueError('Unsupported claim or generic writing')
    if re.search(r'\bI (remember|experienced|witnessed|grew up|was born|met|traveled|travelled|healed)\b|\bmy (childhood|daughter|son|husband|patient|client)\b', all_text, re.I):
        raise ValueError('Possible invented autobiography')
    for old in archive:
        if old['date'] == date:
            if old != note:
                raise ValueError('This date already exists; never overwrite a published reflection')
            continue
        if note['headline'].casefold() == old['headline'].casefold():
            raise ValueError('Repeated headline')
        for a, b, limit in [(text, '\n'.join(old['paragraphs']), .67),
                             (note['intention'], old['intention'], .8),
                             (note['headline'], old['headline'], .8)]:
            if difflib.SequenceMatcher(None, a.casefold(), b.casefold(), autojunk=False).ratio() > limit:
                raise ValueError('Reflection is too similar to the archive')


def render(note, archive_href='healing-journal/index.html'):
    esc = html.escape
    date = dt.date.fromisoformat(note['date'])
    label = date.strftime('%B ') + str(date.day) + date.strftime(', %Y')
    paragraphs = '\n'.join('      <p>' + esc(p) + '</p>' for p in note['paragraphs'])
    return f'''<section id="healing-reflection" aria-labelledby="hv-reflection-title" data-publication-date="{date}">
  <article class="hv-reflection">
    <div class="hv-ornament" aria-hidden="true">☾</div>
    <p class="hv-kicker">A moment for yourself</p>
    <p class="hv-meta"><time datetime="{date}">{label}</time> · {esc(note['theme'])} · 3 min read</p>
    <h2 id="hv-reflection-title">{esc(note['headline'])}</h2>
    <div class="hv-body">
{paragraphs}
    </div>
    <footer class="hv-intention"><span>Carry this into today</span><p>{esc(note['intention'])}</p></footer>
    <a class="hv-archive" href="{archive_href}">Earlier reflections</a>
  </article>
</section>'''


def page(title, description, canonical, content):
    esc = html.escape
    footer = (Path(__file__).resolve().parents[1] / 'network-footer.html').read_text().replace('src="images/', 'src="../images/')
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | HAYVN Healing</title><meta name="description" content="{esc(description)}">
<link rel="canonical" href="https://www.hayvnstudio.com/healing-journal/{canonical}">
<link rel="stylesheet" href="{FONT}"><link rel="stylesheet" href="../css/healing-journal.css?v=20261017"><link rel="stylesheet" href="../css/network-footer.css?v=20261020">
<style>body{{margin:0;background:#0d0a11;color:#d8bd95}} .journal-return{{display:block;max-width:830px;margin:25px auto;padding:0 20px;color:#d8bd95;font:16px Georgia,serif;text-underline-offset:5px}} a:focus-visible{{outline:2px solid #e9d39a;outline-offset:5px}}</style>
</head><body><a class="journal-return" href="../healing.html#healing-reflection">← HAYVN Healing</a>
{content}
{footer}
</body></html>
'''


def prepare(root, note):
    directory = root / 'content/healing-journal'
    archive = [json.loads(p.read_text()) for p in sorted(directory.glob('*.json'))]
    validate(note, archive)
    current = root / 'healing.html'
    source = current.read_text()
    if source.count(START) != 1 or source.count(END) != 1:
        raise ValueError('Expected one bounded reflection block; refusing to alter Healing')
    if re.search(r'data-publication-date="(\d{4}-\d{2}-\d{2})"', source):
        old_date = re.search(r'data-publication-date="(\d{4}-\d{2}-\d{2})"', source)[1]
        if old_date > note['date']:
            raise ValueError('Refusing to roll back the current reflection')
    notes = {n['date']: n for n in archive}
    notes[note['date']] = note
    updated = source.split(START)[0] + START + '\n' + render(note) + '\n' + END + source.split(END)[1]
    outputs = {'healing.html': updated}
    path = f"content/healing-journal/{note['date']}.json"
    outputs[path] = json.dumps(note, ensure_ascii=False, indent=2) + '\n'
    outputs[f"healing-journal/{note['date']}.html"] = page(note['headline'], note['paragraphs'][0][:155], note['date']+'.html', render(note, 'index.html'))
    rows = '\n'.join(f'<p><time datetime="{n["date"]}">{n["date"]}</time><br><a href="{n["date"]}.html">{html.escape(n["headline"])}</a></p>' for n in sorted(notes.values(), key=lambda n: n['date'], reverse=True))
    listing = '<section id="healing-reflection"><div class="hv-reflection"><p class="hv-kicker">A moment for yourself</p><h2>Earlier reflections</h2><div class="hv-body">'+rows+'</div></div></section>'
    listing = listing.replace('<a href=', '<a style="color:#e9d39a;text-underline-offset:5px" href=')
    outputs['healing-journal/index.html'] = page('A moment for yourself', 'Morning reflections on self-kindness, friendship, and a more intentional life.', 'index.html', listing)
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('note', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--allow-historical', action='store_true', help='For archive rebuilds only')
    args = parser.parse_args()
    note = json.loads(args.note.read_text())
    if not args.allow_historical and note['date'] != today():
        raise ValueError('New publications must use today in America/Toronto')
    outputs = prepare(args.root, note)
    changed = [path for path, value in outputs.items() if not (args.root/path).exists() or (args.root/path).read_text() != value]
    if args.check:
        print(json.dumps({'status': 'validated', 'date': note['date'], 'words':len(words(' '.join(note['paragraphs']))), 'changed':changed}))
        return
    # All validation and rendering finish before writes. Publication must be a single Git tree/commit.
    for path in changed:
        target = args.root/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(outputs[path])
    print(json.dumps({'status':'prepared' if changed else 'already-published', 'date':note['date'], 'changed':changed}))


if __name__ == '__main__':
    main()
