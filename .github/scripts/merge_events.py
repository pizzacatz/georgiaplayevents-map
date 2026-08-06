#!/usr/bin/env python3
"""Merge custom event names from Google Calendar feeds into events.ics.

The site's primary feed (events.ics, fetched from pokedata.ovh) carries the
official tournament names. The Georgia Play! Google Calendars carry the names
we actually want to display. Both sides reference the same pokemon.com
tournament URL, so its tournament ID (e.g. 26-05-005436) is the join key:
wherever a calendar event and a pokedata event share an ID, the calendar's
SUMMARY replaces the pokedata SUMMARY. Everything else (times, locations,
descriptions, URLs) is left untouched, so map pins and filters keep working.

Usage:
    merge_events.py <events.ics> <google-ics-url-or-path> [more feeds...]

A Google feed that fails to download is skipped with a warning rather than
failing the run: a Calendar outage should not block the daily feed update.
Only the pokedata file is ever modified, and only when a name changed.
"""

import re
import sys
import urllib.request

TOURNAMENT_ID = re.compile(r"play-pokemon-tournaments/(\d{2}-\d{2}-\d{6})")


def read_feed(source):
    """Return unfolded ICS text from a URL or local path, or None on failure."""
    try:
        if source.startswith("http://") or source.startswith("https://"):
            req = urllib.request.Request(
                source, headers={"User-Agent": "GA-Play-Events-Map/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        else:
            with open(source, encoding="utf-8") as f:
                raw = f.read()
    except Exception as e:
        print(f"WARNING: could not read {source}: {e}")
        return None
    if "BEGIN:VCALENDAR" not in raw:
        print(f"WARNING: {source} is not a calendar feed; skipping.")
        return None
    # Unfold continuation lines (RFC 5545: CRLF followed by a space or tab).
    return re.sub(r"\r?\n[ \t]", "", raw)


def vevents(ics_text):
    return re.findall(r"BEGIN:VEVENT.*?END:VEVENT", ics_text, re.S)


def unescape_text(value):
    return (
        value.replace("\\n", " ")
        .replace("\\N", " ")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
        .strip()
    )


def escape_text(value):
    return (
        value.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")
    )


def collect_overrides(sources):
    """Map tournament ID -> custom SUMMARY from the Google Calendar feeds."""
    overrides = {}
    for source in sources:
        text = read_feed(source)
        if text is None:
            continue
        found = 0
        for ev in vevents(text):
            if re.search(r"^STATUS:CANCELLED", ev, re.M):
                continue
            id_match = TOURNAMENT_ID.search(ev)
            summary_match = re.search(r"^SUMMARY[^:]*:(.*)$", ev, re.M)
            if not id_match or not summary_match:
                continue
            summary = unescape_text(summary_match.group(1))
            if summary:
                overrides[id_match.group(1)] = summary
                found += 1
        print(f"{source}: {found} named events")
    return overrides


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1

    events_path = sys.argv[1]
    overrides = collect_overrides(sys.argv[2:])
    print(f"Total name overrides collected: {len(overrides)}")

    with open(events_path, encoding="utf-8") as f:
        original = f.read()

    replaced = 0

    def merge_event(match):
        nonlocal replaced
        ev = match.group(0)
        id_match = TOURNAMENT_ID.search(ev)
        if not id_match or id_match.group(1) not in overrides:
            return ev
        new_summary = "SUMMARY:" + escape_text(overrides[id_match.group(1)])
        merged, n = re.subn(r"^SUMMARY[^:]*:.*$", new_summary, ev, count=1, flags=re.M)
        if n:
            replaced += 1
        return merged

    merged = re.sub(r"BEGIN:VEVENT.*?END:VEVENT", merge_event, original, flags=re.S)

    print(f"Events renamed from calendar: {replaced}")
    if merged != original:
        with open(events_path, "w", encoding="utf-8") as f:
            f.write(merged)
        print(f"Wrote {events_path}")
    else:
        print("No changes to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
