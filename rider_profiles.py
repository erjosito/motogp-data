"""Collect official rider biographies and season-scoped media references, not images."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from urllib.parse import urlencode, urlsplit
from uuid import UUID

import requests


BASE_URL = "https://api.pulselive.motogp.com/motogp/v1"
DEFAULT_CATALOG = Path(__file__).with_name("rider_profiles.reviewed.json")
COLLECTION_CATALOG = Path(__file__).with_name("rider_profiles.local.json")
ROLES = ("face", "rider_cutout", "bike", "number", "rider_with_bike")


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def uuid_value(value):
    return str(UUID(str(value)))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class ProfileSource:
    """Keep retrieval timestamps with cached responses; never download artwork."""

    def __init__(self, cache, refresh=False):
        self.cache = Path(cache)
        self.refresh = refresh
        self.last_request = 0

    def __call__(self, endpoint, params=None):
        url = f"{BASE_URL}/{endpoint}"
        if params:
            url += "?" + urlencode(sorted(params.items()))
        path = self.cache / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if path.exists() and not self.refresh:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if saved["source_url"] != url or saved["source_sha256"] != digest(saved["payload"]):
                raise ValueError(f"Invalid cached profile response: {path}")
            return saved
        time.sleep(max(0, 2 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        response = requests.get(url, timeout=60)
        if response.status_code == 429:
            raise requests.HTTPError(
                f"Official profile API rate limit; honor Retry-After "
                f"{response.headers.get('Retry-After', 'not supplied')} before resuming",
                response=response,
            )
        response.raise_for_status()
        payload = response.json()
        saved = {
            "source_url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "source_sha256": digest(payload), "payload": payload,
        }
        write_json(path, saved)
        return saved


def identity_links(cache):
    """Only explicit links in official result snapshots can join the two APIs."""
    candidates = {}
    results = {}

    def visit(value, evidence):
        if isinstance(value, list):
            for item in value:
                visit(item, evidence)
        elif isinstance(value, dict):
            rider = value.get("rider")
            if isinstance(rider, dict):
                references = {rider[key] for key in ("riders_api_uuid", "riders_id") if rider.get(key)}
                if len(references) > 1:
                    raise ValueError(f"Conflicting official profile IDs in {evidence['snapshot']}")
                if references and rider.get("id"):
                    profile_id = uuid_value(references.pop())
                    rider_id = uuid_value(rider["id"])
                    legacy_id = rider.get("legacy_id")
                    results.setdefault(rider_id, set()).add(profile_id)
                    candidates.setdefault(profile_id, {}).setdefault((rider_id, legacy_id), {
                        "rider_id": rider_id, "legacy_id": legacy_id,
                        "method": "official_results_explicit_profile_uuid", **evidence,
                    })
            for item in value.values():
                visit(item, evidence)

    paths = sorted(Path(cache).glob("*.json"))
    if not paths:
        raise ValueError("No official result snapshots found; populate the historical cache first.")
    for path in paths:
        raw = path.read_bytes()
        snapshot = json.loads(raw)
        if not isinstance(snapshot, dict) or "standings" not in snapshot or "events" not in snapshot:
            continue
        visit(snapshot, {
            "snapshot": path.name, "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        })
    if not candidates:
        raise ValueError("Result snapshots contain no explicit rider/profile UUID links.")
    links = {}
    for profile_id, options in candidates.items():
        rows = list(options.values())
        if len(rows) == 1 and len(results[rows[0]["rider_id"]]) == 1:
            links[profile_id] = rows[0]
        else:
            links[profile_id] = {
                "rider_id": None, "legacy_id": None, "method": "ambiguous_official_results_links",
                "reason": "Upstream identifiers are not one-to-one; no automatic join.",
                "candidates": rows,
            }
    return links


def optional_text(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("Expected text in official profile.")
    return value.strip() or None


def asset_reference(url, role):
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ("photos.motogp.com", "www.motogp.com"):
        raise ValueError(f"Unexpected official artwork URL: {url}")
    return {
        "role": role, "original_url": url,
        "rights": {
            "license": "NOASSERTION", "approval": "unapproved",
            "rights_holder": None, "creator": None, "credit": None,
            "terms_url": "https://www.motogp.com/en/legal-notice",
            "reason": "Official hosting does not establish display, cropping or redistribution permission.",
        },
        "technical": {
            "width_px": None, "height_px": None, "has_transparency": None,
            "inspection": "not_inspected",
        },
    }


def normalize_profile(response, link, checked_on=None):
    raw = response["payload"]
    profile_id = uuid_value(raw["id"])
    birth_date = optional_text(raw.get("birth_date"))
    checked_on = checked_on or date.today()
    if birth_date and date.fromisoformat(birth_date) > checked_on:
        raise ValueError(f"Future birth date for {profile_id}")
    height = (raw.get("physical_attributes") or {}).get("height")
    if height is not None:
        if isinstance(height, bool) or not isinstance(height, (int, float)) or not math.isfinite(height) or height < 0:
            raise ValueError(f"Invalid height for {profile_id}")
        # The source uses zero for unavailable measurements.
        height = height or None
    if link and link["legacy_id"] is not None and link["legacy_id"] != raw.get("legacy_id"):
        raise ValueError(f"Legacy ID disagrees with explicit result/profile link: {profile_id}")
    careers = []
    seen = set()
    for step in raw.get("career") or []:
        step_id = uuid_value(step["id"])
        if step_id in seen:
            raise ValueError(f"Duplicate career step for {profile_id}")
        seen.add(step_id)
        season = step["season"]
        if isinstance(season, bool) or not isinstance(season, int) or not 1949 <= season <= checked_on.year + 1:
            raise ValueError(f"Invalid career season for {profile_id}")
        team = step.get("team") or {}
        category = step.get("category") or {}
        pictures = step.get("pictures") or {}
        face = pictures.get("portrait")
        cutout = (pictures.get("profile") or {}).get("main")
        bike = (pictures.get("bike") or {}).get("main")
        careers.append({
            "career_step_id": step_id, "season": season,
            "category_id": category.get("id"), "category": category.get("name"),
            "team_id": team.get("id"),
            "team_name": optional_text(step.get("sponsored_team")),
            "team_name_scope": "career_step_sponsored_team",
            "constructor": (team.get("constructor") or {}).get("name"),
            "number": step.get("number"),
            "media": {
                "face": asset_reference(face, "face"),
                "rider_cutout": asset_reference(cutout, "rider_cutout"),
                "bike": asset_reference(bike, "bike"),
                "number": asset_reference(pictures.get("number"), "number"),
                "rider_with_bike": None,
            },
        })
    return {
        "rider_id": link["rider_id"] if link else None,
        "profile_id": profile_id, "legacy_id": raw.get("legacy_id"),
        "name": " ".join(filter(None, [optional_text(raw.get("name")), optional_text(raw.get("surname"))])),
        "identity": link or {"method": "unmatched", "reason": "No explicit result-source UUID link."},
        "biography": {
            "birth_date": birth_date, "birth_city": optional_text(raw.get("birth_city")),
            "birth_country": optional_text(raw.get("birth_country")), "height_cm": height,
            "measurement_scope": "source_reported_at_retrieval_not_historical",
        },
        "source": {key: response[key] for key in ("source_url", "retrieved_at", "source_sha256")},
        "careers": sorted(careers, key=lambda row: (row["season"], row["career_step_id"])),
    }


def coverage(profiles, season):
    steps = [step for profile in profiles for step in profile["careers"]]
    return {
        "profiles": len(profiles),
        "matched_results_riders": sum(profile["rider_id"] is not None for profile in profiles),
        "identity_conflicts": sum(
            profile["identity"]["method"] == "ambiguous_official_results_links" for profile in profiles
        ),
        "birth_dates": sum(profile["biography"]["birth_date"] is not None for profile in profiles),
        "birthplaces": sum(profile["biography"]["birth_city"] is not None for profile in profiles),
        "heights": sum(profile["biography"]["height_cm"] is not None for profile in profiles),
        "career_steps": len(steps),
        "media_references": {role: sum(step["media"][role] is not None for step in steps) for role in ROLES},
        "requested_season_media": {
            role: sum(step["media"][role] is not None for step in steps if step["season"] == season)
            for role in ROLES
        },
        "approved_official_media": 0,
    }


def read_enrichment(rider_id, path=None):
    path = Path(path or os.environ.get("MOTOGP_RIDER_CATALOG", DEFAULT_CATALOG))
    if not path.exists():
        if path != DEFAULT_CATALOG:
            raise ValueError(f"Configured rider catalog is missing: {path}")
        return {"status": "not_collected", "profile": None}
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog["format_version"] != 1:
        raise ValueError("Unsupported rider catalog version.")
    matches = [profile for profile in catalog["profiles"] if profile["rider_id"] == rider_id]
    if len(matches) > 1:
        raise ValueError(f"Duplicate rider in enrichment catalog: {rider_id}")
    return {
        "status": "available" if matches else "not_collected",
        "profile": matches[0] if matches else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=date.today().year)
    parser.add_argument("--profile-id", action="append", default=[], help="Additional official profile UUID, e.g. a retired rider.")
    parser.add_argument("--results-cache", type=Path, default=Path("historical_cache"))
    parser.add_argument("--cache", type=Path, default=Path("historical_cache") / "rider_profiles")
    parser.add_argument("--output", type=Path, default=COLLECTION_CATALOG)
    parser.add_argument("--manifest", type=Path, help="Optional shareable counts/hash manifest, without profile records.")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    if not 1949 <= args.season <= date.today().year:
        parser.error("Season must be between 1949 and the current year.")
    if args.manifest and args.manifest.resolve() == args.output.resolve():
        parser.error("Manifest path must differ from the profile catalog path.")
    links = identity_links(args.results_cache)
    source = ProfileSource(args.cache, args.refresh)
    directory = source("riders", {"seasonYear": args.season})
    if not isinstance(directory["payload"], list) or not directory["payload"]:
        raise ValueError("Official rider directory is empty or has an unsupported shape.")
    ids = {uuid_value(row["id"]) for row in directory["payload"]}
    additional = {uuid_value(value) for value in args.profile_id}
    profiles = []
    for profile_id in sorted(ids | additional):
        response = source(f"riders/{profile_id}")
        if uuid_value(response["payload"]["id"]) != profile_id:
            raise ValueError("Profile endpoint returned a different rider.")
        profile = normalize_profile(response, links.get(profile_id))
        if profile_id in ids and not any(step["season"] == args.season for step in profile["careers"]):
            raise ValueError(f"Directory rider has no requested-season career step: {profile_id}")
        profiles.append(profile)
        print(f"{profile['name']}: {len(profile['careers'])} career steps; "
              f"identity={profile['identity']['method']}", flush=True)
    result = {
        "format_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "requested_season": args.season, "directory_source": {
            key: directory[key] for key in ("source_url", "retrieved_at", "source_sha256")
        },
        "scope": "Requested-season directory plus explicitly requested retired profiles; not all historical riders.",
        "media_policy": "References only; unknown rights are unapproved; no image bytes or stale-season fallback.",
        "coverage": coverage(profiles, args.season), "profiles": profiles,
    }
    write_json(args.output, result)
    if args.manifest:
        raw_output = args.output.read_bytes()
        write_json(args.manifest, {
            "format_version": 1, "created_at": result["created_at"],
            "requested_season": args.season, "additional_profile_ids": sorted(additional),
            "directory_source": result["directory_source"], "scope": result["scope"],
            "coverage": result["coverage"], "media_policy": result["media_policy"],
            "catalog": {
                "name": args.output.name, "bytes": len(raw_output),
                "sha256": hashlib.sha256(raw_output).hexdigest(),
            },
            "redistribution_clearance": "not-established",
        })
    print(json.dumps(result["coverage"], indent=2))


if __name__ == "__main__":
    main()
