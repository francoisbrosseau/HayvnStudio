#!/usr/bin/env python3
"""Suppress stale RSS items without changing the website or archived reflections."""
import argparse
import datetime as dt
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from zoneinfo import ZoneInfo


class Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self.current = []

    def handle_data(self, text):
        if self.current is not None:
            self.current.append(text)

    def handle_endtag(self, tag):
        if tag == 'p' and self.current is not None:
            self.paragraphs.append(''.join(self.current))
            self.current = None


def guarded_feed(source, website, note, today):
    """Retain only today's exact published reflection; otherwise expose no RSS items."""
    rss = ET.fromstring(source)
    channel = rss.find('channel')
    if channel is None:
        raise ValueError('RSS channel is missing; do not publish malformed XML')
    match = re.search(r'data-publication-date="(\d{4}-\d{2}-\d{2})"', website)
    valid_note = (isinstance(note, dict) and note.get('date') == today and match
                  and match.group(1) == today
                  and html.escape(note.get('headline', '')) in website)
    expected_url = 'https://www.hayvnstudio.com/healing-journal/' + today + '.html'
    removed = 0
    for item in list(channel.findall('item')):
        parser = Paragraphs()
        parser.feed(item.findtext('description') or '')
        valid = (valid_note and item.findtext('guid') == expected_url
                 and item.findtext('link') == expected_url
                 and item.findtext('title') == note.get('headline')
                 and parser.paragraphs == note.get('paragraphs', [])
                     + ['Carry this into today', note.get('intention')])
        if not valid:
            channel.remove(item)
            removed += 1
    if not removed:
        return source, False
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding='unicode') + '\n', True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    today = dt.datetime.now(ZoneInfo('America/Cancun')).date().isoformat()
    note_path = args.root / 'content/healing-journal' / (today + '.json')
    try:
        note = json.loads(note_path.read_text()) if note_path.exists() else None
    except (ValueError, OSError):
        note = None
    path = args.root / 'healing-reflections.xml'
    output, changed = guarded_feed(path.read_text(), (args.root / 'healing.html').read_text(), note, today)
    if changed:
        path.write_text(output)
    count = len(ET.fromstring(output).findall('./channel/item'))
    print(json.dumps({'date': today, 'changed': changed, 'eligible_items': count,
                      'status': 'fresh' if count else 'skip_no_current_reflection'}))


if __name__ == '__main__':
    main()
