#!/usr/bin/env python3
"""Verify the same dated reflection on the public page, archive and feed."""
import datetime as dt
import html
import json
from pathlib import Path
import time
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
from healing_newsletter_guard import guarded_feed

root = Path(__file__).resolve().parents[1]
date = dt.datetime.now(ZoneInfo("America/Cancun")).date().isoformat()
note = json.loads((root / ("content/healing-journal/" + date + ".json")).read_text())
origin = "https://www.hayvnstudio.com/"
paths = ["healing.html", "healing-reflections.xml", "healing-journal/" + date + ".html", "healing-journal/index.html"]
last_error = None
for attempt in range(12):
    try:
        pages = []
        for path in paths:
            with urllib.request.urlopen(origin + path, timeout=15) as result:
                pages.append(result.read().decode())
        feed, changed = guarded_feed(pages[1], pages[0], note, date)
        assert not changed and len(ET.fromstring(feed).findall("./channel/item")) == 1
        for paragraph in note["paragraphs"] + [note["intention"]]:
            assert html.escape(paragraph) in pages[0] and html.escape(paragraph) in pages[2]
        assert html.escape(note["headline"]) in pages[2]
        assert date + ".html" in pages[3]
        print("LIVE_VERIFIED " + date + ": reflection, archive, index and matching feed")
        break
    except (AssertionError, OSError, ValueError) as error:
        last_error = error
        if attempt == 11:
            raise RuntimeError("Public reflection verification failed after deployment") from last_error
        time.sleep(10)
