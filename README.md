# GA Play! Events Map

Interactive map of Pokémon play events in Georgia — companion to the
[Georgia Play! Events Calendar](https://georgiaplayevents.com/). Live at
the domain in [CNAME](CNAME), served by GitHub Pages from this repo.

The map plots upcoming TCG / VGC / Pokémon GO events as colored pins
(blue / red / green), with per-game and per-tier filters, a date picker,
and a "home base" address marker.

## How the data flows

```
pokedata.ovh ICS feed          Georgia Play! Google Calendars (public ICS)
 (official tournament data)     (custom event names)
        │                              │
        ▼                              ▼
  GitHub Action: "Update events feed" (daily 08:00 UTC + manual)
        │  1. fetch pokedata feed for GA events (from 2 days back)
        │  2. merge_events.py overlays calendar names onto the feed
        │  3. commit events.ics if changed
        ▼
   events.ics (committed to repo, served same-origin)
        │
        ▼
   index.html — loads ./events.ics, geocodes locations, renders pins
```

- **`index.html`** is the whole site: MapLibre GL map, filters, and the
  ICS-parsing/rendering logic. It loads `events.ics` same-origin first;
  if that's missing or invalid it falls back to fetching pokedata live
  through public CORS proxies.
- **`.github/workflows/update-events.yml`** runs daily at 08:00 UTC
  (~3–4 am ET), on manual dispatch, and whenever the workflow file
  itself changes. It fetches the pokedata feed server-side (no CORS
  limits), merges in calendar names, and commits the result.
- **`.github/scripts/merge_events.py`** (stdlib Python, no deps) joins
  the two sources by **pokemon.com tournament ID** (the
  `NN-NN-NNNNNN` in `play-pokemon-tournaments/` URLs) and replaces only
  each matched event's `SUMMARY`. Locations, times, descriptions, and
  URLs stay pokedata's, so geocoding and filters are unaffected.

## Basemap

The map is [MapLibre GL JS](https://maplibre.org/) rendering CARTO's
**Dark Matter** vector basemap. Event pins live in a single clustered
GeoJSON source; the pins themselves are inline SVG, so the map depends
on no third-party image host to draw its own markers.

The `CARTO_KEY` near the top of the map code is a **public, client-side
basemap token**. This is a static site with no server and no build step,
so anything the browser needs ships in the page source by design —
the key is protected by the **domain allowlist on the CARTO account**,
not by secrecy. Keep that allowlist restricted to `georgiaplayevents.com`.

CARTO's TileJSON returns tile URLs without the key attached, so a key on
the style URL alone would only ever tag that one request. `transformRequest`
stamps it onto every `cartocdn.com` request instead, which keeps usage
attributed to the account and keeps the map working if CARTO extends its
key requirement to vector tiles (it already enforces one on raster).
The free tier covers 5M tile requests per calendar month.

## Event names come from the Google Calendars

The map shows each event's `SUMMARY` **verbatim**. For an event to get
its custom name:

1. The event must exist on one of the Georgia Play! Google Calendars
   listed in the workflow (currently: Pokémon GO, TCG Challenges, TCG
   Cups, TCG Prereleases, VGC).
2. The calendar entry must contain its **pokemon.com tournament link**
   (the description is the usual place). No link → no match → the map
   shows pokedata's official tournament name instead.
3. Cancelled calendar entries are ignored.

Rename an event on the calendar and the map picks it up on the next
daily run. "SAVE THE DATE" placeholders without a tournament link are
fine — they simply don't override anything until a link is added.

### Adding another calendar

1. In Google Calendar settings, make the calendar public.
2. Get its calendar ID — either from *Settings → Integrate calendar*,
   or by base64-decoding the `cid=` parameter of a share link.
3. The public feed URL is
   `https://calendar.google.com/calendar/ical/<calendar-id>/public/basic.ics`
   (encode the `@` as `%40`).
4. Append that URL to `GOOGLE_CALENDAR_ICS_URLS` in
   [.github/workflows/update-events.yml](.github/workflows/update-events.yml).

## Game/tier classification (filters & pin colors)

Classification is intentionally **independent of the display name**:

- **Game** (TCG / VGC / GO) comes from the pokedata event's URL and raw
  summary keywords.
- **Tier** (Cup / Challenge / Prerelease) comes from the anchor text in
  the pokedata description (e.g. "League Cup @ STORE"), which survives
  the name merge untouched.

So custom calendar names never break filtering.

## Geocoding

Locations are geocoded in the browser via Nominatim (rate-limited,
cached in `localStorage`). Addresses Nominatim can't resolve are pinned
via the `manualOverrides` table near the top of the script in
`index.html` — the browser console logs the exact string to add when a
lookup fails.

## Local development

No build step. Serve the folder and open it:

```
python3 -m http.server
```

Test the name merge against the committed feed without touching it:

```
cp events.ics /tmp/test.ics
python3 .github/scripts/merge_events.py /tmp/test.ics <calendar-ics-url>...
```

## Troubleshooting

- **An event shows the official name, not the calendar name** — the
  calendar entry is missing its pokemon.com link, is cancelled, or the
  event isn't on any merged calendar. Check the "Merge names from
  Google Calendars" step in the latest Actions run: it logs per-feed
  event counts and how many events were renamed.
- **Feed looks stale** — run the workflow manually (Actions → "Update
  events feed" → Run workflow). If pokedata is down the run fails
  loudly; the site keeps serving the last committed feed, with the
  browser falling back to live proxies.
- **A pin is in the wrong place or missing** — see Geocoding above.
