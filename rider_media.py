"""Season-scoped, rights-reviewed local portrait selection shared by both apps."""

import hashlib
import json
from pathlib import Path

from category_scope import canonical_category


ROOT = Path(__file__).parent


def read_portrait(rider_id, season, categories, root=ROOT):
    if season is None:
        return None
    categories = {canonical_category(category) for category in categories}
    catalog = json.loads((root / "media_catalog.json").read_text(encoding="utf-8"))
    if catalog["format_version"] != 1:
        raise ValueError("Unsupported media catalog version.")
    for asset in catalog["assets"]:
        if (
            asset["rider_id"] != rider_id or asset["season"] != season
            or asset["role"] != "face" or canonical_category(asset["category"]) not in categories
            or asset["rights"]["approval"] != "approved_editorial"
        ):
            continue
        derivatives = asset.get("display_derivatives", [])
        if not derivatives:
            continue
        for variant in derivatives:
            path = (root / variant["path"]).resolve()
            if not path.is_relative_to((root / "assets" / "riders").resolve()):
                raise ValueError("Portrait derivative must be inside assets/riders.")
            if (
                variant["license"] != asset["rights"]["license"]
                or variant["source_sha256"] != asset["technical"]["sha256"]
            ):
                raise ValueError("Portrait derivative rights/source do not match its approved original.")
            data = path.read_bytes()
            if len(data) != variant["bytes"] or hashlib.sha256(data).hexdigest() != variant["sha256"]:
                raise ValueError(f"Portrait derivative hash mismatch: {variant['path']}")
        return asset
    return None
