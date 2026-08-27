# Technical Vocabulary — this project, three ways

The same story told three times: (1) in full industry jargon, (2) in plain
language with the matching technical term after each phrase, (3) as a
glossary table anchoring every term to the moment it appeared in this
project. Read 1 to test yourself, 2 to decode it, 3 to make it stick.

---

## 1. The jargon-dense version

### What it is

GA Play! Events Map is a **static site** — `index.html` plus a committed
data file, no build step, no backend — deployed via **GitHub Pages** off a
**custom domain** (see `CNAME`). It renders a **Leaflet** map (dark
**tile layer** from CartoDB) of Pokémon TCG/VGC/GO events, with **marker
clustering** (`leaflet.markercluster`) so dense metro areas collapse into
a single expandable pin, colored **markers** (blue/red/green **icon**
variants for TCG/VGC/GO), a **date picker**, per-tier **filter checkboxes**,
and a **home base** marker persisted across sessions.

### The data pipeline

The site is fed by a **scheduled GitHub Action** (`.github/workflows/update-events.yml`,
**cron**-triggered daily plus **workflow_dispatch** for manual runs, with a
**concurrency group** to prevent overlapping runs) that does **server-side
fetching** of an upstream **ICS feed** (RFC 5545 **iCalendar** format) from
pokedata.ovh, scoped by **query-string parameters** encoding game type,
tier, state, and a rolling **start date**. This sidesteps the **CORS
(Cross-Origin Resource Sharing)** restriction the browser would otherwise
hit calling that API directly. The Action validates the response contains
a `BEGIN:VCALENDAR` **anchor string**, then runs `merge_events.py` — a
**stdlib-only** (dependency-free) Python script that treats each Google
Calendar feed's SUMMARY as an **override** keyed by a **regex-extracted**
**join key**: the `NN-NN-NNNNNN` **tournament ID** parsed out of each
event's pokemon.com URL. It **unfolds** ICS **continuation lines** (a
CRLF followed by a space, per the RFC), builds an ID→name **lookup table**
from every non-**CANCELLED** calendar VEVENT, then does a targeted
**regex substitution** that replaces only the `SUMMARY` line of matching
pokedata VEVENTs, leaving location/time/description/URL fields as the
**source of truth** untouched. The workflow then **git commits** the
result only if it changed, with a **rebase-and-retry loop** to survive a
race against a concurrent push.

### The client

`index.html` **same-origin** fetches the committed `events.ics` first
(no CORS issue since it's served from the same domain); only if that's
missing or malformed does it fall back to a **fetch-through-proxy chain**
(`CORS_PROXIES`, tried in order) hitting the live pokedata API through
public **CORS proxy** services, one of which wraps the response in
**JSON** (`allorigins`) and one that passes text through raw (`codetabs`).
The feed is **parsed** with `ical.js` into `ICAL.Event` objects. Each
event runs through **classification logic** the code itself calls the
**"Split Brain" filter** — game type (TCG/VGC/GO) is detected from **raw
summary keyword matching** plus URL substring checks, while **tier**
(Cup/Challenge/Prerelease) is detected from an `<a>` **anchor tag's** inner
text inside the HTML-bearing `description` field — deliberately
**decoupled** from the display name so a calendar-supplied custom title
never breaks filtering. Locations are turned into map coordinates by
**geocoding**: a **manual override table** (hardcoded lat/lon for
addresses the geocoder can't parse) is checked first, then a
**localStorage-backed cache** (`pokemonGeoCache`), and only on a cache miss
does it call the **Nominatim** (OpenStreetMap) geocoding API, **rate-limited**
client-side with a **debounce-like sleep** between calls to respect
Nominatim's usage policy. A separately cached **home base** marker (address
+ coordinates in `localStorage`) lets a user recenter the map on their own
location across visits.

---

## 2. The plain-language version

This is a plain website with no server of its own (**static site**) — one
big HTML file plus a data file, checked into GitHub and hosted for free
by GitHub's own hosting (**GitHub Pages**) under its own custom web
address (**custom domain**, from the `CNAME` file). It draws an
interactive map (**Leaflet**, a JavaScript mapping library) using a dark
map background pulled from a map-tile provider (**tile layer**), and
groups nearby pins into a single number-badge when zoomed out so the map
doesn't get cluttered (**marker clustering**). Pins come in three colors
for TCG/VGC/Pokémon GO events (**colored markers**), and there's a date
picker, checkboxes to filter by event tier, and a "home" pin the user can
set that's remembered next time they visit.

Where does the event list come from? A robot task that GitHub itself runs
on a timer (**scheduled GitHub Action**, once a day, or by hand via a
button) fetches a calendar file (**ICS feed**, the same standard format
you'd export from Google Calendar or Outlook) from a Pokémon-events site
called pokedata.ovh, asking specifically for Georgia events from a couple
days ago onward. It does this fetching itself, from GitHub's own servers,
rather than asking your browser to — browsers refuse to fetch data from a
different website unless that website explicitly allows it (a security
rule called **CORS**), and doing it server-side skips that rule entirely.
After downloading, it checks the response actually looks like a calendar
file before trusting it, then hands it to a second little script
(`merge_events.py`) whose whole job is: for each event on the Georgia
Play! Google Calendars, find its matching event in the pokedata file by
matching the *same tournament number* embedded in both events' web links
(the **join key**, extracted with a **pattern match / regex**), and if
found, swap in the calendar's title for pokedata's official one — nothing
else about the event (time, place, link) gets touched. Only if the
resulting file is actually different does it get saved back into the
repository (**git commit**), with some retry logic in case two runs
happen to write at nearly the same moment.

When you load the page, it first tries to grab that pre-fetched calendar
file straight from the same website you're on (**same-origin fetch** — no
CORS problem there, since it's not a different site). Only if that file
is missing or broken does it fall back to fetching pokedata.ovh live
through a couple of public "CORS-bypass" relay services (**CORS
proxies**), trying each one until one actually returns real data. Once it
has calendar data, a library (**ical.js**) turns the raw text into
JavaScript objects it can read. Then, for every event, the code decides
two independent things: what *game* it is (TCG/VGC/GO — guessed from
keywords in the title and the web link) and what *tier* it is
(Cup/Challenge/Prerelease — guessed from the text inside a link buried in
the event's description). The code's own comment calls this the **"Split
Brain" filter**, because it deliberately keeps those two guesses separate
from whatever custom name a calendar organizer typed in, so renaming an
event on the calendar never accidentally hides it from a filter.

To put a pin on the map, the address text needs a latitude/longitude
(**geocoding**). First it checks a small built-in list of addresses that
a geocoding service couldn't figure out on its own (**manual overrides**,
hand-entered coordinates); then it checks a save file in the browser
(**localStorage cache**) for an address it's already looked up before; only
if neither hits does it actually ask an online geocoding service
(**Nominatim**, part of OpenStreetMap) — and because that free service
asks callers not to hammer it, the code deliberately waits about a second
between each lookup (**rate limiting**). The user's own "home base" address
gets the same save-to-browser treatment, so it's still set the next time
they open the map.

---

## 3. Glossary — term → meaning → where it happened here

### Site & deployment

| Term | Plain meaning | In this project |
|---|---|---|
| **static site** | a website with no server-side code, just files | `index.html` + `events.ics`, no build step, per README |
| **GitHub Pages** | GitHub's free static-site hosting | serves this repo directly |
| **custom domain** | your own URL instead of the host's default one | domain named in `CNAME` |
| **same-origin** | request to the site's own domain, not a third party | `fetchLocalFeed()` fetching `./events.ics` |

### Mapping (Leaflet)

| Term | Plain meaning | In this project |
|---|---|---|
| **tile layer** | the map imagery, loaded as small image squares | CartoDB dark tiles, `index.html:192` |
| **marker clustering** | grouping nearby pins into one badge when zoomed out | `L.markerClusterGroup()`, `index.html:196` |
| **icon** | the pin image/shape for a marker | `createColorIcon()`; blue/red/green/gold variants |
| **popup** | the info box that opens when you click a pin | `.bindPopup(html)` in `renderEventsForDate()` |

### Calendar data & the merge pipeline

| Term | Plain meaning | In this project |
|---|---|---|
| **ICS / iCalendar (RFC 5545)** | the standard calendar-file text format | both `events.ics` and the Google Calendar feeds |
| **VEVENT** | one event block inside an ICS file | matched via `BEGIN:VEVENT...END:VEVENT` regex in `merge_events.py` |
| **unfold(ing) continuation lines** | rejoining a long ICS field that RFC 5545 wraps across lines | `re.sub(r"\r?\n[ \t]", "", raw)` in `read_feed()` |
| **join key** | the shared ID used to match records from two sources | the `NN-NN-NNNNNN` tournament ID from the pokemon.com URL |
| **regex / pattern match** | searching text for a structural pattern | `TOURNAMENT_ID = re.compile(...)` |
| **override** | a value that replaces another, more "official" one | calendar `SUMMARY` replacing pokedata's `SUMMARY` |
| **cron schedule** | run automatically at a fixed recurring time | `cron: '0 8 * * *'` in `update-events.yml` |
| **workflow_dispatch** | a manual "run now" trigger for a GitHub Action | listed as a trigger alongside `schedule` |
| **concurrency group** | prevents two runs of the same job from overlapping | `group: update-events` in the workflow |
| **git commit / rebase-and-retry** | saving a change; retrying a push after someone else pushed first | the "Commit if changed" step's retry loop |

### Client-side fetch & CORS

| Term | Plain meaning | In this project |
|---|---|---|
| **CORS (Cross-Origin Resource Sharing)** | the browser rule blocking cross-site requests unless allowed | the reason `fetchPokemonEvents()` needs proxies at all |
| **CORS proxy** | a third-party relay that adds the missing permission headers | `CORS_PROXIES` array: allorigins, codetabs |
| **fallback chain** | trying options in order until one works | local feed → proxy 1 → proxy 2 in `fetchPokemonEvents()` |
| **ICS parsing library (ical.js)** | turns raw ICS text into usable JS objects | `ICAL.parse(rawText)`, `ICAL.Event` |

### Classification ("Split Brain" filter)

| Term | Plain meaning | In this project |
|---|---|---|
| **keyword/substring detection** | deciding a category by checking for known words | `rawSummaryUp.indexOf('TCG')` etc. in `doesEventPassFilters()` |
| **anchor tag inner text** | the visible label of an `<a href>` link | tier detection parses the anchor inside `description` |
| **decoupling** | keeping two things independent so one can change without breaking the other | game/tier detection is independent of the display `SUMMARY`, per README |
| **filter matrix** | a table of conditions deciding pass/fail per category | the `if (isTcg) {...} else if (isVgc) {...}` block |

### Geocoding

| Term | Plain meaning | In this project |
|---|---|---|
| **geocoding** | converting a street address into latitude/longitude | `getCoordinates(addr)` |
| **Nominatim** | OpenStreetMap's free geocoding search API | the `fetch('https://nominatim.openstreetmap.org/search...')` call |
| **rate limiting** | deliberately slowing requests to respect a service's usage policy | `await sleep(1100)` after each Nominatim call |
| **manual override table** | hand-entered fallback values for cases automation can't resolve | `manualOverrides` object, `index.html:216` |
| **localStorage cache** | saving key→value data in the browser between visits | `pokemonGeoCache` and `pokemonHomeCoords`/`pokemonHomeAddress` |
