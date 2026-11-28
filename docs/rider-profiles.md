# Rider biographies and infographic media

## What is collected

`rider_profiles.py` collects factual biography fields and **references to images**,
not official image files. It does not update riders, results, events or timing
tables in SQL. Biography and media are additive to the rider career API.

The official public sources are:

- Directory: `https://api.pulselive.motogp.com/motogp/v1/riders?seasonYear=2026`
- Detail: `https://api.pulselive.motogp.com/motogp/v1/riders/{profile_uuid}`
- Human-readable profile, for example:
  <https://www.motogp.com/en/riders/marc-marquez/23e50438-a657-4fb0-a190-3262b5472f29>
- Height unit cross-check (169 cm for Marc):
  <https://www.ducati.com/ww/en/racing/motogp/ducati-lenovo-team-marc-marquez>

These are undocumented upstream APIs, not a stability or completeness guarantee.
No open license for the official photography or number artwork was established.
The [existing data-rights notice](data-rights.json) still applies: public access
alone is not permission to redistribute, crop, remove backgrounds or display an
image. The user subsequently stated that they made the supplied artwork and
that it is free to use. The supplied manifest records official source URLs;
no specific open-license identifier or adaptation terms were supplied.

## Reproduce the local catalog

First populate official archive snapshots as documented in the repository's
historical/standings import sections. They supply explicit cross-API rider IDs.
Then run from the repository root:

```powershell
python rider_profiles.py --season 2026

# Optionally include a retired rider: this UUID is Valentino Rossi's profile ID.
python rider_profiles.py --season 2026 --profile-id d6f009a8-5a57-49b1-8c68-a9c78349d500 --manifest exports\rider-profiles-2026-11-27.manifest.json
```

Default output: `rider_profiles.local.json`, Git-ignored. Successful source
responses, their original retrieval timestamps and hashes are cached in
`historical_cache\rider_profiles`. Repeating a command reuses those responses;
`--refresh` requests them again. Uncached requests are at least two seconds
apart. HTTP errors, including rate limits, stop the command explicitly; successful
responses already cached can be reused on the next run. Publication of a complete
catalog is atomic, so a failed run does not replace the previous output.

`--results-cache`, `--cache` and `--output` accept alternative local paths.
`--manifest` writes a shareable counts/hash report without the profile records.
Do not commit a raw profile dump or this unreviewed full catalog. Review rights
before publicly distributing it. Raw biography prose and social links are not
copied into the normalized catalog.

The directory may include wildcards, test/replacement riders and all three
modern classes. This is **not the complete historical rider population**.
Every directory member must actually have a requested-season career step in its
detail response; the collector refuses mismatched source results rather than
assuming that a query parameter was honored. Extra retired profiles are explicit.

The first collection (2026-11-27) contains **105 profiles**: 104 directory entries
plus Valentino Rossi, with 104 explicit results-ID matches and one unmatched
profile. All 105 have a supplied birth date and birthplace; 91 have a nonzero
height. Across 846 career steps there are 555 face-slot, 532 rider-cutout-slot,
354 bike-slot and 318 number-artwork references. These are **reference counts,
not distinct photographs or visually verified roles**. In 2026 alone the source
supplies 107 cutout-slot, three bike-slot and four number references across all
career steps, but no portrait-slot images. These reference counts are not a grant to use the other official media. The
[manifest](../exports/rider-profiles-2026-11-27.manifest.json)
records the measured scope and catalog hash.

## Contract (format version 1)

| Record | Fields and meaning |
|---|---|
| Catalog | `requested_season`, `created_at`, directory URL/retrieval/hash, measured `coverage`, `profiles[]` |
| Identity | `rider_id`: existing results UUID or null; `profile_id`: separate official profile UUID; `legacy_id`: source legacy ID |
| Join evidence | `identity.method`, archive snapshot filename and SHA-256; conflicting candidate links retained explicitly |
| Biography | Nullable ISO `birth_date`, `birth_city`, `birth_country`, `height_cm` |
| Provenance | `source.source_url`, original `retrieved_at` timestamp and canonical-JSON `source_sha256` |
| Career step | `career_step_id`, `season`, `category_id`, source `category`, `team_id`, `team_name`, constructor and number |
| Media slots | Nullable `face`, `rider_cutout`, `bike`, `number`, `rider_with_bike` |
| Media reference | `role`, exact `original_url`, separate `rights` and `technical` records |

Use the **results `rider_id`**, never a name or race number, as the application
join key. Official result payloads explicitly expose `riders_api_uuid` and/or
`riders_id`. The collector uses only those links and cross-checks legacy IDs.
Disagreeing explicit fields fail validation. Non-one-to-one links are held with
`rider_id: null` and `ambiguous_official_results_links`; no identities are merged.
Profiles with no link are `unmatched`. Neither can silently enrich a rider.

The height is the profile's reported measurement at retrieval, not a measurement
for every historical season. A source zero or null is unavailable, not zero
centimetres. Age should be derived from birth date for a specified date; the
upstream mutable age field is not persisted.

Historical `team_name` comes only from the career step's `sponsored_team`.
The nested team's name can already be its **current** sponsor name even in an
old career step, so it is not used as a historical-name fallback. Several steps
in the same year remain separate. The catalog does not claim that every mid-year
team change or every historical livery is represented.

Source slots map to roles as follows: `pictures.portrait` -> face,
`pictures.profile.main` -> rider cutout, `pictures.bike.main` -> bike,
`pictures.number` -> number artwork. These are **source classifications, not
visual QA**: a bike image might include its rider, and a PNG is not proof of
transparency. Unknown dimensions and alpha remain null/`not_inspected`.
The inspected API has no dedicated rider-with-bike slot, so that slot remains
null, not fabricated by compositing or mislabeling a bike photograph.

Every official reference starts with `rights.license: NOASSERTION` and
`rights.approval: unapproved`, with unknown creator/credit and the official
terms URL. No current-season media falls back to another year's kit, bike or
number design. A numeric race number does not grant rights to the rider's
distinctive artwork or typography.

## User-supplied number artwork

The user supplied the PNGs and stated, "I did the artwork myself, it is free
to use." The supplied manifest also records official source URLs. No specific
open-license identifier was supplied. The files are preserved unchanged in a
Git-ignored private bundle, separate from the
unreviewed official profile media references and from portrait rights.
Source links are shown with each design; any additional conditions of the
permission still need to be recorded if supplied.

To stage a copy without altering the source, populate the historical result
cache and run:

```powershell
python stage_rider_numbers.py "C:\Users\jomore\Downloads\motogp-rider-numbers" "assets\rider-numbers"
```

The destination must not already exist. The command checks explicit
profile-to-results UUID links, legacy IDs, source paths, PNGs, lengths and
SHA-256 hashes. It stores deduplicated originals and a catalog without local
source paths. An explicitly configured `MOTOGP_RIDER_NUMBERS` points to an
alternative private bundle directory; missing or corrupt configured content
is an error. With no default bundle, artwork is simply unavailable. Exact-scope
requests with multiple different images for the same rider, season, class and
number are withheld; rider-identity display can choose one deterministically.
MotoE entries are retained but are not displayed because that class is not
covered by the app. Each displayed item is labeled with its own season and
class, never substituted as current artwork for a different year.
When the source includes unmatched profile IDs or legacy category-3 entries
with unknown class and number, `--hold-unmatched` records them in `held` with
the reason instead of including them in the displayable catalog. Without this
option, the command rejects the bundle.

For this small bundle, private container-image packaging is simpler than
placing image blobs in SQL. The Docker build contexts include the bundle if
it has been staged; a Git-only build cannot recreate it. Use private image
storage and retain the original bundle securely for rebuilds. If the collection
grows or needs independent updates, private Azure Blob Storage plus metadata
keyed by rider UUID, season, class and number is a better separate asset store;
no storage account or SQL schema change is required for this initial approach.

## App integration without a redesign

Classic season statistics and `/api/riders/{results_rider_id}` career seasons
include recorded Q2 poles. Each API season adds `gp_poles` (integer or null),
`gp_poles_q2_events` (integer) and `gp_poles_method: "recorded_q2_wins"`.
The shared class-format rules support MotoGP from 2013 and Moto2/Moto3 from
2019. Only classified results from finished Q2 are counted, once per event
and actual class; conflicting recorded positions for an event are withheld.
The coverage count is that rider's recorded classified Q2 events, not all
race weekends. No qualifying evidence, Q1-only participation, unsupported
formats and standings-only historical seasons retain null poles, not zero.
A recorded non-winning Q2 result permits zero. These counts describe partial
imports, not complete historical or penalty-adjusted starting-grid pole totals.
Qualifying rows never inflate race appearances, wins, points or title totals.

The additive read-only endpoint is:

```text
GET /api/riders/{results_rider_id}/enrichment
```

It returns `{ "status": "available", "profile": { ... } }` for a verified match,
or `{ "status": "not_collected", "profile": null }`. It reads the reviewed
`rider_profiles.reviewed.json` subset (21 threshold-selected champions, with no career media)
catalog or the file configured by `MOTOGP_RIDER_CATALOG`. An explicitly configured
but missing file, malformed data or duplicate rider match is an error, not an
empty success. There is no upstream request or SQL write during an app request.

The preview container includes the reader and that minimal reviewed subset,
**not the unreviewed local catalog**. A configured replacement must also be
intentionally reviewed before mounting. Riders outside the subset return
`not_collected`; the existing career endpoint still works. The collector keeps
writing `rider_profiles.local.json`, never overwriting the reviewed runtime file.

### Champion biography scope

The initial expansion uses **at least two premier-class championships OR at least
five combined lower-class championships**. Premier means 500cc/MotoGP; lower
classes include 350cc, 250cc/Moto2, 125cc/Moto3, 80cc and 50cc. Titles won in
different classes in the same year count separately. A total of five titles
split as one premier plus four lower does not meet either threshold.

There are **21 qualifying sourced biographies**: 17 multi-premier champions,
plus Carlo Ubbiali, Jim Redman, Angel Nieto and Anton Mang through the lower-class
criterion. All have a source-reported birth date and city; 20 have a supplied
birth country and seven a nonzero reported height. Missing measurements stay
null, and Jim Redman's absent source birth-country field is not filled from his
racing nationality. Historical source facts remain attributed, not independently
certified measurements. The original short career text is generated from
recorded final-title seasons rather than copied from upstream biography prose.

Eligibility is established by the **recorded official final tables** in the
verified SQL export. These are sufficient positive evidence for the selected
riders, but their counts are not complete career-title totals: for example,
missing historical tables undercount Ubbiali and Nieto. Marc qualifies from
completed seasons alone; the separately clinched 2026 title is not disguised as
a completed final table. Provisional standings are never counted. This
selection does not change any SQL data or imply that remaining source gaps
have been resolved. It does not lower the requested thresholds.

Reproduce the candidate selection and factual subset:

```powershell
python build_champion_biographies.py --archive exports\motogp-data-2026-11-27-standings.tar.xz
```

Default output is Git-ignored `champion_biographies.local.json`. The command
verifies the export, selects qualifying rank-one final records, uses only
unambiguous official identity links and reuses the timestamped profile cache.
It refuses an empty selection or an unmatched qualifying rider. After reviewing
the results, explicitly select `--output rider_profiles.reviewed.json` to publish
the factual slice. The shared reader/API and both containers already consume
that file; no separate app-specific biography catalogs are needed. Acquisition
of these factual records **does not approve any additional image**. Non-Marc
riders continue to use existing initials unless separate approved media exists.

The SQL export remains a SQL snapshot, not an export of this optional local
catalog; retain the profile catalog and its source cache separately if needed.

## Infographic design decisions

| Use | Preferred source/master | Display treatment |
|---|---|---|
| Podium, comparison avatar, rider hero | Consistent head/shoulders framing, face unobscured, crop room; preferably >=600 px shortest side | Face crop with `object-fit: cover`; a photograph need not be transparent |
| Rider or bike cutout | Original transparent PNG/WebP with genuine alpha, preferably >=1200 px on longest side | `object-fit: contain`, preserve aspect ratio and leave breathing room |
| Personal number | Rights-cleared SVG, otherwise high-resolution transparent PNG/WebP | Keep the actual graphic, not an approximation with a generic font |
| Rider with bike | Period-correct photo with verified rider/season/team context | Contain the whole subject; do not imply an old livery is current |
| Venue header | Rights-cleared landscape original, preferably >=1600 px wide | Shallow crop away from chart labels; not a decorative chart background |

Dimensions are preferences, not acquisition blockers. Preserve originals and
derive responsive WebP/AVIF only where allowed; never upscale low-resolution
sources to claim quality. Do not remove backgrounds without permission for
modification. Keep image copyright, trademark/personality rights, credit,
cropping permission and app display approval distinct. Missing or unapproved
imagery uses initials/plain numeric labels, not an unrelated or generated rider.

`media_catalog.json` holds a small separately reviewed set of reusable references
with actual dimensions, creator, source page/original URL and period context.
Copyright permission alone does not establish endorsement or every other right.
The initial set has two author-dedicated public-domain photographs of helmeted
riders with bikes in 2025, plus one high-resolution, unobscured Marc Marquez
portrait from 2026 under **CC BY-SA 4.0** (Denkmit). The portrait requires
attribution, a license link, identification of changes and share-alike treatment
for image adaptations. It is not a universally licensed transparent asset pack.
Apply EXIF orientation before cropping: that original is encoded landscape but
displays upright at 3848 x 5776. A coherent full-grid portrait set is still absent.

## Packaged portrait display contract

The approved Marc 2026 portrait now has two local head-and-shoulders WebP
derivatives in `assets/riders`: `marc-marquez-2026-portrait-320.webp` (320x400,
18,772 bytes) and `marc-marquez-2026-portrait-640.webp` (640x800, 51,600 bytes).
The 9.75 MB original is not shipped. EXIF orientation is applied before the
upright crop `[350,380,3350,4130]`; no background is removed. Attribution and
CC BY-SA 4.0 are embedded and recorded in the adjacent `LICENSE.txt`.

The existing portrait asset in `media_catalog.json` owns a `display_derivatives`
array: repository-relative `path`, dimensions, byte count, SHA-256, original
`source_sha256`, adaptation `changes`, `license` and `license_url`. Its parent
retains the verified results `rider_id`, season/class/team, creator and source.
`rider_media.read_portrait(rider_id, season, categories)` selects only an
approved face for that exact season and actual class and checks the local
derivative hashes/source/license. No remote image fetch occurs. All-career,
historical, other-class and unpictured selections intentionally return no face;
helmeted bike photos are never promoted to portraits.

Both apps must show creator, source and license links, describe the crop/resize
adaptation and label the photo's season/team honestly. Adapted image contributions
remain CC BY-SA 4.0; this is not a new license for the application, SQL data,
visible marks or personality rights. Biography enrichment remains independently
keyed through the reviewed factual catalog, not through names or image presence.

Paddock's career identity card requests an explicit **2026 / premier** portrait
reference, labels that season and team beside it, and preserves the 4:5 crop.
It is not a claim about a rider's appearance throughout their career. Unpictured
riders use initials and a plain numeric race number. Only the reviewed factual
subset is included, so missing biography fields are omitted rather than guessed.

The preview API exposes `GET /api/riders/{rider_id}/portrait?season=2026&category=premier`
for display metadata and scoped `/portrait/{width}` URLs for the checked local
WebP variants. Both endpoints also work under `/paddock`. Wrong-season/class
metadata returns `not_collected`; unavailable image variants return404. No
original or unapproved image URL is returned as display media. Creator/source
and license links stay visible; an adaptation disclosure gives the full changes.

Classic's **Riders -> Pilot Profile** uses stable results rider IDs as selector
values and SQL parameters, with display names used only as labels. Its compact
identity panel shows the reviewed birth facts, explicitly retrieval-dated height
and biography source. The photo appears only for the selected 2026 season when
the filtered records include MotoGP; All-career, older-year, other-class and
unpictured views use initials without changing the existing career analytics.
Creator/source/license/adaptation credits remain visible below the photo.
Number artwork also sits beside the profile name, Home championship rider-card
names and rider-named profile chart titles, including both comparison riders.
Charts use a native inline artwork/title row above the plot instead of
duplicating the name in Plotly's title. Existing plain chart titles remain
when artwork is unavailable. Championship cards use the official standing's
rider ID when available, otherwise an unambiguous ID from the scoped race rows;
ambiguous/missing IDs never match artwork by name or number.
Artwork is read/verified once per rider per app run and reference credits are
shown once per rider in the view, without removing the existing scoped gallery.
It is rider identity, not season-specific evidence:
`read_identity_number(results_rider_id)` uses the latest available design for
that stable rider ID, independently of the selected year/class or absent race
numbers. Multiple latest designs have a deterministic category/number/hash
tie-break so the display does not flicker. Its actual year/class/source remain
visibly labeled as a reference, not as the artwork used in the selected race.
The helper verifies the chosen bytes and does not change portrait rights or
the exact-scope `read_number` / gallery rules. Missing artwork leaves the existing
name/initials unchanged.
Classic packages the reviewed factual file, approved media metadata, the two
small WebPs/license notice and the separately staged user-supplied number bundle,
never the portrait source package or full local biography catalog.
Invalid configured enrichment or packaged-media integrity errors are reported,
not silently presented as an ordinary unpictured rider.

## Circuit context already present

`circuit_catalog.json` / `circuit_catalog.py` already supply six current-layout
outlines (Jerez, Le Mans, Assen, Mugello, Phillip Island and Valencia), official
length/corner facts and source attribution. Geometry is OpenStreetMap-derived
under ODbL, rendered as original scalable diagrams. Its current-layout facts
must not be presented as the geometry of every historical race.

Paddock's `GET /api/circuit-context?name=<circuit-name>` uses the existing exact
normalized aliases, projects the sourced outline with preserved proportions,
and supplies attribution plus2026 facts. Session pages place this compact context
before analysis. Historical selections explicitly identify it as a current
reference, not the selected year's track; unsupported venues omit the graphic.

Record attendance must retain year and race-day/weekend scope; only the sourced
Le Mans 2025 weekend record is currently supplied. Other attendance is unknown,
not zero. Start/finish, direction and sector boundaries are not inferred from
the order of geometry points or evenly divided track distance. Venue photographs
and comprehensive historical layouts remain acquisition gaps.
