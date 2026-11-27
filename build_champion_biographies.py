"""Build a factual biography subset selected by recorded official championship wins."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import tarfile

from category_scope import canonical_category
from export_data import verify_export
from rider_profiles import ProfileSource, identity_links, normalize_profile, write_json


PREMIER = {"500cc", "MotoGP"}
LOWER = {"350cc", "250cc", "Moto2", "125cc", "Moto3", "80cc", "50cc"}


def select_champions(rows):
    """Counts are eligibility evidence, not a reconstruction of missing career titles."""
    titles = {}
    winners = {}
    for row in rows:
        if str(row["is_final"]) != "1" or str(row["position"]) != "1":
            continue
        category = canonical_category(row["category"])
        if category not in PREMIER | LOWER:
            raise ValueError(f"Unsupported championship class: {category}")
        season = int(row["season_year"])
        key = season, category
        rider_id = row["rider_id"]
        if key in winners and winners[key] != rider_id:
            raise ValueError(f"Conflicting official champions for {season} {category}")
        winners[key] = rider_id
        evidence = {
            "season": season, "category": category, "source_url": row["source_url"],
        }
        titles.setdefault(rider_id, {})[key] = evidence
    selected = {}
    for rider_id, evidence in titles.items():
        final_tables = sorted(evidence.values(), key=lambda row: (row["season"], row["category"]))
        premier = sum(row["category"] in PREMIER for row in final_tables)
        lower = len(final_tables) - premier
        if premier >= 2 or lower >= 5:
            selected[rider_id] = {
                "premier_final_records": premier, "lower_class_final_records": lower,
                "counts_are": "recorded_final_tables_not_complete_career_totals",
                "final_tables": final_tables,
            }
    return selected


def factual_summary(evidence):
    by_class = {}
    for row in evidence["final_tables"]:
        by_class.setdefault(row["category"], []).append(str(row["season"]))
    detail = "; ".join(
        f"{category}: {', '.join(years)}" for category, years in by_class.items()
    )
    return f"Recorded official title-winning seasons include {detail}. This is archive evidence, not a complete career-title total."


def build_catalog(archive_path, results_cache, source):
    manifest = verify_export(archive_path)
    with tarfile.open(archive_path, "r:xz") as archive:
        with archive.extractfile("tables/dbo.championship_standings.csv") as binary, \
                io.TextIOWrapper(binary, encoding="utf-8", newline="") as text:
            selected = select_champions(csv.DictReader(text))
    if not selected:
        raise ValueError("No riders meet the championship thresholds in this snapshot.")
    links = identity_links(results_cache)
    by_result = {
        link["rider_id"]: (profile_id, link)
        for profile_id, link in links.items() if link["rider_id"]
    }
    profiles = []
    for rider_id, evidence in sorted(selected.items()):
        if rider_id not in by_result:
            raise ValueError(f"Qualifying rider has no unambiguous official profile link: {rider_id}")
        profile_id, link = by_result[rider_id]
        response = source(f"riders/{profile_id}")
        if response["payload"]["id"] != profile_id:
            raise ValueError(f"Official profile response has wrong identity: {rider_id}")
        profile = normalize_profile(response, link)
        # Ship factual records only; image discovery is not display permission.
        profile["careers"] = []
        profile["selection_evidence"] = evidence
        profile["biography"]["career_summary"] = factual_summary(evidence)
        profile["biography"]["career_summary_scope"] = "original_text_from_recorded_final_tables"
        profiles.append(profile)
        print(f"{profile['name']}: {evidence['premier_final_records']} premier / "
              f"{evidence['lower_class_final_records']} lower-class final records", flush=True)
    return {
        "format_version": 1,
        "reviewed_on": datetime.now(timezone.utc).date().isoformat(),
        "scope": "Threshold-selected sourced factual biographies; no official artwork or copied biography prose.",
        "selection_policy": {
            "premier_minimum": 2, "combined_lower_classes_minimum": 5,
            "operator": "OR", "premier_classes": sorted(PREMIER), "lower_classes": sorted(LOWER),
            "evidence": "Official rank-one final standings only; qualifying counts are lower bounds where source tables are missing.",
            "current_season": "Provisional standings are excluded; no assertion that a clinched title is a final table.",
        },
        "selection_source": {
            "archive": Path(archive_path).name,
            "archive_sha256": hashlib.sha256(Path(archive_path).read_bytes()).hexdigest(),
            "snapshot_database_time_utc": manifest["snapshot_database_time_utc"],
        },
        "coverage": {
            "profiles": len(profiles),
            "birth_dates": sum(profile["biography"]["birth_date"] is not None for profile in profiles),
            "birth_cities": sum(profile["biography"]["birth_city"] is not None for profile in profiles),
            "birth_countries": sum(profile["biography"]["birth_country"] is not None for profile in profiles),
            "reported_heights": sum(profile["biography"]["height_cm"] is not None for profile in profiles),
        },
        "profiles": sorted(profiles, key=lambda profile: profile["name"]),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path, help="Verified portable SQL snapshot.")
    parser.add_argument("--results-cache", type=Path, default=Path("historical_cache"))
    parser.add_argument("--cache", type=Path, default=Path("historical_cache") / "rider_profiles")
    parser.add_argument("--output", type=Path, default=Path("champion_biographies.local.json"))
    args = parser.parse_args(argv)
    result = build_catalog(args.archive, args.results_cache, ProfileSource(args.cache))
    write_json(args.output, result)
    print(f"Written {len(result['profiles'])} factual profiles to {args.output}")


if __name__ == "__main__":
    main()
