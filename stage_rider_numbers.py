"""Stage user-supplied number artwork without publishing it in the repository."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from PIL import Image

from rider_profiles import identity_links


def stage(source, destination, results_cache, hold_unmatched=False):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    links = identity_links(results_cache)
    assets = []
    held = []
    files = {}
    for row in manifest["files"]:
        profile_id = str(UUID(row["rider_id"]))
        link = links.get(profile_id)
        if hold_unmatched and (row["category"] == "dorsales-legacy-3" or not link or not link["rider_id"]):
            held.append({
                "profile_id": profile_id, "season": row["season"], "category": row["category"],
                "number": row["number"], "source_url": row["source_url"],
                "reason": "unknown_class_and_number" if row["category"] == "dorsales-legacy-3"
                else "no_unambiguous_results_id",
            })
            continue
        if not link or not link["rider_id"]:
            raise ValueError(f"No unambiguous results ID for profile {profile_id}")
        if link["legacy_id"] is not None and link["legacy_id"] != row["legacy_id"]:
            raise ValueError(f"Legacy ID mismatch for profile {profile_id}")
        source_url = urlsplit(row["source_url"])
        if source_url.scheme != "https" or source_url.hostname != "photos.motogp.com":
            raise ValueError(f"Unexpected artwork source URL: {row['source_url']}")
        if (type(row["season"]) is not int or type(row["number"]) is not int
                or row["season"] < 1949 or row["number"] < 0
                or row["category"] not in ("MotoGP", "Moto2", "Moto3", "MotoE")):
            raise ValueError(f"Invalid artwork scope for profile {profile_id}")
        path = Path(row["file"]).resolve(strict=True)
        if not path.is_relative_to(source) or not path.is_file():
            raise ValueError(f"Artwork path is outside source directory: {path}")
        data = path.read_bytes()
        if len(data) != row["bytes"]:
            raise ValueError(f"Artwork size mismatch: {path}")
        with Image.open(path) as image:
            if image.format != "PNG":
                raise ValueError(f"Artwork is not PNG: {path}")
            image.verify()
        digest = hashlib.sha256(data).hexdigest()
        files[digest] = path
        assets.append({
            "rider_id": link["rider_id"],
            "profile_id": profile_id,
            "legacy_id": row["legacy_id"],
            "season": row["season"],
            "category": row["category"],
            "number": row["number"],
            "source_url": row["source_url"],
            "sha256": digest,
            "bytes": len(data),
            "file": f"{digest}.png",
        })
    destination.mkdir(parents=True)
    for digest, path in files.items():
        shutil.copyfile(path, destination / f"{digest}.png")
        if hashlib.sha256((destination / f"{digest}.png").read_bytes()).hexdigest() != digest:
            raise ValueError(f"Copied artwork hash mismatch: {path}")
    catalog = {"format_version": 1, "assets": assets}
    if held:
        catalog["held"] = held
    (destination / "catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return len(assets), len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Directory containing the supplied manifest")
    parser.add_argument("destination", type=Path, help="New private staging directory")
    parser.add_argument("--results-cache", type=Path, default=Path("historical_cache"))
    parser.add_argument("--hold-unmatched", action="store_true",
                        help="Record unmatched IDs and legacy category-3 rows as held, not displayable")
    args = parser.parse_args()
    assets, files = stage(args.source, args.destination, args.results_cache, args.hold_unmatched)
    print(f"Staged {assets} records and {files} distinct PNG files in {args.destination}")
    if args.hold_unmatched:
        catalog = json.loads((args.destination / "catalog.json").read_text(encoding="utf-8"))
        print(f"Held {len(catalog.get('held', []))} records; see catalog.json for reasons")


if __name__ == "__main__":
    main()
