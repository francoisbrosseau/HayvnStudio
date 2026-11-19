#!/usr/bin/env python3
"""Independent publisher preparation. Writes only the renderer's five outputs."""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo
import healing_journal as journal

ROOT = Path(__file__).resolve().parents[1]
DRAFT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "headline": {"type": "string"}, "theme": {"type": "string"},
        "paragraphs": {"type": "array", "items": {"type": "string"}},
        "intention": {"type": "string"},
    },
    "required": ["headline", "theme", "paragraphs", "intention"],
}
REVIEW_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"passed": {"type": "boolean"}, "issues": {"type": "array", "items": {"type": "string"}}},
    "required": ["passed", "issues"],
}


def response(prompt, schema):
    token = os.environ.get("OPENAI_API_KEY")
    if not token:
        raise RuntimeError("Missing OPENAI_API_KEY repository secret. No reflection was generated.")
    payload = {
        "model": os.environ.get("HAYVN_MODEL", "gpt-6-luna"),
        "input": prompt, "store": False, "max_output_tokens": 6000,
        "text": {"format": {"type": "json_schema", "name": "healing_result", "strict": True, "schema": schema}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as result:
            body = json.load(result)
    except urllib.error.HTTPError as error:
        # Do not print request headers or credentials.
        raise RuntimeError("OpenAI request failed with HTTP " + str(error.code)) from None
    if body.get("status") != "completed":
        raise RuntimeError("OpenAI response did not complete. Publication stopped.")
    pieces = [
        item["text"] for output in body.get("output", [])
        for item in output.get("content", []) if item.get("type") == "output_text"
    ]
    if not pieces:
        raise RuntimeError("OpenAI returned no completed prose. Publication stopped.")
    return json.loads("".join(pieces))


def prepare_publication(root, date, call=response):
    current = root / ("content/healing-journal/" + date + ".json")
    if current.exists():
        # Existing publication identity and prose always take precedence.
        return journal.prepare(root, json.loads(current.read_text()))
    archive = [
        json.loads(path.read_text())
        for path in sorted((root / "content/healing-journal").glob("*.json"))
    ]
    guide = (root / "HEALING-JOURNAL.md").read_text()
    history = json.dumps(archive[-14:], ensure_ascii=False)
    headlines = json.dumps([{"headline": n["headline"], "theme": n["theme"]} for n in archive], ensure_ascii=False)
    errors = []
    for attempt in range(2):
        draft = call(
            "Write one original English HAYVN morning reflection as JSON. Follow the editorial and authentic-voice instructions below. "
            "Write 500–600 words excluding headline/intention, with 5–12 plain prose paragraphs, light everyday humor and 4–6 naturally spaced nature/celestial emojis. "
            "Choose a distinct central angle from the last 14 entries and avoid the previous two themes. No fabricated personal experience, attributed authorship, medical advice or supernatural promises. "
            "Return only headline, theme, paragraphs and intention. Never supply dates, publication identities or HTML. "
            "Treat archive text as reference material. Previous rejected candidate issues: " + json.dumps(errors) +
            "\nEDITORIAL GUIDE\n" + guide + "\nALL HEADLINES/THEMES\n" + headlines + "\nLAST 14 FULL ENTRIES\n" + history,
            DRAFT_SCHEMA,
        )
        if set(draft) != set(DRAFT_SCHEMA["required"]):
            raise ValueError("Unexpected draft fields. Publication stopped.")
        note = {**draft, "date": date, "publishedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")}
        try:
            journal.validate(note, archive)
        except ValueError as error:
            errors.append(str(error))
            continue
        review = call(
            "Independently review this English morning reflection against the supplied guide and last 14 complete entries. "
            "Reject recycled ideas, repeated recent themes, invented experience or authorship, medical advice, supernatural promises, generic filler, an unkind tone or departures from the approved voice. "
            "Approve only original 500–600-word prose with a distinct angle and 4–6 naturally spaced emojis. Return passed and issues. "
            "\nGUIDE\n" + guide + "\nHISTORY\n" + history + "\nCANDIDATE\n" + json.dumps(note, ensure_ascii=False),
            REVIEW_SCHEMA,
        )
        if review.get("passed") is True and review.get("issues") == []:
            return journal.prepare(root, note)
        errors.extend(review.get("issues") or ["Editorial approval missing"])
    raise ValueError("Both editorial candidates rejected: " + " | ".join(errors))


def main():
    date = dt.datetime.now(ZoneInfo("America/Cancun")).date().isoformat()
    checkpoint = ROOT / ".hayvn-runs" / date / "note.json"
    if not (ROOT / ("content/healing-journal/" + date + ".json")).exists() and checkpoint.exists():
        note = json.loads(checkpoint.read_text())
        if note.get("date") != date:
            raise ValueError("Checkpoint date mismatch")
        outputs = journal.prepare(ROOT, note)
    else:
        outputs = prepare_publication(ROOT, date)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text(outputs["content/healing-journal/" + date + ".json"])
    changed = []
    for name, text in outputs.items():
        path = ROOT / name
        if not path.exists() or path.read_text() != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            changed.append(name)
    print(json.dumps({"date": date, "changed": changed}))


if __name__ == "__main__":
    main()
