import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import healing_journal as journal
import publish_healing as publisher


class PublisherTests(unittest.TestCase):
    def test_existing_note_never_calls_api_and_preserves_identity(self):
        path = sorted((ROOT / "content/healing-journal").glob("*.json"))[-1]
        note = json.loads(path.read_text())
        def forbidden(*args):
            self.fail("Existing dates must never generate a second note")
        self.assertEqual(publisher.prepare_publication(ROOT, note["date"], forbidden), journal.prepare(ROOT, note))

    def test_rejected_candidates_are_bounded_and_write_nothing(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "content/healing-journal").mkdir(parents=True)
            (root / "HEALING-JOURNAL.md").write_text("Approved test guide")
            calls = []
            def rejected(*args):
                calls.append(args)
                return {"headline": "Too short", "theme": "Test", "paragraphs": ["short"] * 5, "intention": "Test"}
            with self.assertRaisesRegex(ValueError, "Both editorial candidates rejected"):
                publisher.prepare_publication(root, "2026-11-19", rejected)
            self.assertEqual(len(calls), 2)
            self.assertEqual(list((root / "content/healing-journal").iterdir()), [])

    def test_approved_draft_prepares_five_outputs_without_writing(self):
        import copy
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "content/healing-journal").mkdir(parents=True)
            source = (ROOT / "healing.html").read_text()
            (root / "healing.html").write_text(source)
            (root / "HEALING-JOURNAL.md").write_text("Approved test guide")
            note = json.loads(sorted((ROOT / "content/healing-journal").glob("*.json"))[-1].read_text())
            draft = {key: copy.deepcopy(note[key]) for key in publisher.DRAFT_SCHEMA["required"]}
            calls = []
            def approved(prompt, schema):
                calls.append(schema)
                return copy.deepcopy(draft) if schema == publisher.DRAFT_SCHEMA else {"passed": True, "issues": []}
            outputs = publisher.prepare_publication(root, "2099-01-01", approved)
            self.assertEqual(len(calls), 2)
            self.assertEqual(set(outputs), {"healing.html", "content/healing-journal/2099-01-01.json",
                                           "healing-journal/2099-01-01.html", "healing-journal/index.html",
                                           "healing-reflections.xml"})
            self.assertIn("2099-01-01.html", outputs["healing-reflections.xml"])
            self.assertEqual(outputs["healing.html"].split(journal.START)[0], source.split(journal.START)[0])
            self.assertEqual(outputs["healing.html"].split(journal.END)[1], source.split(journal.END)[1])
            self.assertFalse((root / "content/healing-journal/2099-01-01.json").exists())

    def test_missing_key_does_not_make_network_request(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Missing OPENAI_API_KEY"):
                publisher.response("Test", publisher.DRAFT_SCHEMA)
