import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('journal', ROOT/'scripts/healing_journal.py')
journal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journal)


class JournalTests(unittest.TestCase):
    def setUp(self):
        latest = sorted((ROOT/'content/healing-journal').glob('*.json'))[-1]
        self.note = json.loads(latest.read_text())

    def test_approved_note_and_idempotent_render(self):
        journal.validate(self.note, [])
        first = journal.prepare(ROOT, self.note)
        for path, output in first.items():
            self.assertEqual((ROOT/path).read_text(), output, path)

    def test_same_date_cannot_be_overwritten(self):
        changed = copy.deepcopy(self.note)
        changed['headline'] = 'A different headline'
        with self.assertRaisesRegex(ValueError, 'already exists'):
            journal.validate(changed, [self.note])

    def test_feed_delivers_complete_reflection_with_stable_identity(self):
        feed = journal.render_feed(self.note)
        channel = ET.fromstring(feed).find('channel')
        self.assertEqual(len(channel.findall('item')), 1)
        item = channel.find('item')
        self.assertEqual(item.findtext('title'), self.note['headline'])
        self.assertEqual(item.findtext('guid'), 'https://www.hayvnstudio.com/healing-journal/' + self.note['date'] + '.html')
        text = []
        class Text(HTMLParser):
            def handle_data(self, value):
                text.append(value)
        Text().feed(item.findtext('description'))
        for paragraph in self.note['paragraphs'] + [self.note['intention']]:
            self.assertIn(paragraph, text)
        self.assertEqual(feed, journal.render_feed(copy.deepcopy(self.note)))

    def test_feed_markup_is_escaped_and_timestamp_is_validated(self):
        note = copy.deepcopy(self.note)
        note['paragraphs'][0] = 'A & B <do not run> 🌙'
        feed = ET.fromstring(journal.render_feed(note))
        self.assertIn('A &amp; B &lt;do not run&gt; 🌙', feed.findtext('channel/item/description'))
        note['publishedAt'] = '2026-11-01T07:00:00'
        with self.assertRaisesRegex(ValueError, 'timezone'):
            journal.render_feed(note)

    def test_recycled_note_rejected(self):
        recycled = copy.deepcopy(self.note)
        recycled['date'] = '2026-10-18'
        with self.assertRaisesRegex(ValueError, 'Repeated headline'):
            journal.validate(recycled, [self.note])

    def test_padding_and_unsupported_claims_rejected(self):
        for bad in ['A short paragraph.', 'Unlock your potential. ' * 40]:
            changed = copy.deepcopy(self.note)
            changed['paragraphs'] = [bad]*5
            with self.assertRaises(ValueError):
                journal.validate(changed, [])

    def test_unrelated_healing_content_is_preserved(self):
        current = (ROOT/'healing.html').read_text()
        output = journal.prepare(ROOT, self.note)['healing.html']
        strip = lambda s: s.split(journal.START)[0] + s.split(journal.END)[1]
        self.assertEqual(strip(current), strip(output))
        self.assertLess(current.index('class="hero"'), current.index(journal.START))
        self.assertLess(current.index(journal.END), current.index('class="bio-section"'))
        self.assertIn('aria-label="Explore Lunara by HAYVN tarot"', output)

    def test_invalid_markers_fail_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'healing.html').write_text('untouched existing site')
            with self.assertRaisesRegex(ValueError, 'bounded reflection'):
                journal.prepare(root, self.note)
            self.assertEqual((root/'healing.html').read_text(), 'untouched existing site')


if __name__ == '__main__':
    unittest.main()
