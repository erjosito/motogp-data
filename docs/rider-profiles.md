# Rider biographies and infographic media

## What is collected

`rider_profiles.py` collects factual biography fields and **references to images**,
not official image files. It does not update riders, results, events or timing
tables in SQL. The existing rider career API remains unchanged.

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
is not permission to redistribute, crop, remove backgrounds or display an image.

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
career steps, but no portrait-slot images. None of the official media has
established reuse permission. The [manifest](../exports/rider-profiles-2026-11-27.manifest.json)
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

## App integration without a redesign

The additive read-only endpoint is:

```text
GET /api/riders/{results_rider_id}/enrichment
```

It returns `{ "status": "available", "profile": { ... } }` for a verified match,
or `{ "status": "not_collected", "profile": null }`. It reads the reviewed
`rider_profiles.reviewed.json` subset (currently Marc only, with no career media)
catalog or the file configured by `MOTOGP_RIDER_CATALOG`. An explicitly configured
but missing file, malformed data or duplicate rider match is an error, not an
empty success. There is no upstream request or SQL write during an app request.

The preview container includes the reader and that minimal reviewed subset,
**not the unreviewed local catalog**. A configured replacement must also be
intentionally reviewed before mounting. Riders outside the subset return
`not_collected`; the existing career endpoint still works. The collector keeps
writing `rider_profiles.local.json`, never overwriting the reviewed runtime file.

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

## Circuit context already present

`circuit_catalog.json` / `circuit_catalog.py` already supply six current-layout
outlines (Jerez, Le Mans, Assen, Mugello, Phillip Island and Valencia), official
length/corner facts and source attribution. Geometry is OpenStreetMap-derived
under ODbL, rendered as original scalable diagrams. Its current-layout facts
must not be presented as the geometry of every historical race.

Record attendance must retain year and race-day/weekend scope; only the sourced
Le Mans 2025 weekend record is currently supplied. Other attendance is unknown,
not zero. Start/finish, direction and sector boundaries are not inferred from
the order of geometry points or evenly divided track distance. Venue photographs
and comprehensive historical layouts remain acquisition gaps.
