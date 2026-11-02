import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('guard', ROOT/'scripts/healing_newsletter_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
renderer_spec = importlib.util.spec_from_file_location('journal', ROOT/'scripts/healing_journal.py')
journal = importlib.util.module_from_spec(renderer_spec)
renderer_spec.loader.exec_module(journal)


class NewsletterGuardTests(unittest.TestCase):
    def setUp(self):
        self.note = json.loads(sorted((ROOT/'content/healing-journal').glob('*.json'))[-1].read_text())
        self.source = journal.render_feed(self.note)
        self.website = (ROOT/'healing.html').read_text()

    def check_empty(self, website, note, date, source=None):
        output, changed = guard.guarded_feed(source or self.source, website, note, date)
        self.assertTrue(changed)
        self.assertEqual(ET.fromstring(output).findall('./channel/item'), [])
        again, changed = guard.guarded_feed(output, website, note, date)
        self.assertFalse(changed)
        self.assertEqual(output, again)

    def test_today_is_preserved_byte_for_byte(self):
        output, changed = guard.guarded_feed(self.source, self.website, self.note, self.note['date'])
        self.assertFalse(changed)
        self.assertEqual(output, self.source)

    def test_yesterday_is_suppressed_when_publication_fails(self):
        self.check_empty(self.website, None, '2099-12-31')

    def test_today_json_with_stale_website_is_suppressed(self):
        self.check_empty('', self.note, self.note['date'])

    def test_wrong_content_or_identity_is_suppressed(self):
        for tag in ['title', 'guid', 'description']:
            rss = ET.fromstring(self.source)
            rss.find('./channel/item/' + tag).text = 'wrong content'
            self.check_empty(self.website, self.note, self.note['date'], ET.tostring(rss, encoding='unicode'))


if __name__ == '__main__':
    unittest.main()
