"""Read verified rider number artwork for identity or exact historical scope."""

import hashlib
import json
import os
from pathlib import Path

from category_scope import canonical_category


DEFAULT_BUNDLE = Path(__file__).parent / "assets" / "rider-numbers"


def _catalog(bundle):
    configured = os.environ.get("MOTOGP_RIDER_NUMBERS")
    root = Path(bundle if bundle is not None else configured or DEFAULT_BUNDLE).resolve()
    if not root.exists() and bundle is None and not configured:
        return root, []
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    if catalog["format_version"] != 1:
        raise ValueError("Unsupported rider number catalog version.")
    return root, catalog["assets"]


def _verified(root, asset):
    path = (root / asset["file"]).resolve()
    if not path.is_relative_to(root) or path.parent != root:
        raise ValueError("Number artwork must be inside the configured bundle.")
    data = path.read_bytes()
    if len(data) != asset["bytes"] or hashlib.sha256(data).hexdigest() != asset["sha256"]:
        raise ValueError(f"Number artwork hash mismatch: {asset['file']}")
    return asset, data


def read_number(rider_id, season, category, number, bundle=None):
    if season is None or category is None or number is None:
        return None
    category = canonical_category(category)
    root, assets = _catalog(bundle)
    matches = [asset for asset in assets if asset["rider_id"] == rider_id
               and asset["season"] == season and asset["category"] == category
               and asset["number"] == number]
    if not matches:
        return None
    if len({asset["sha256"] for asset in matches}) != 1:
        return None
    return _verified(root, matches[0])


def read_identity_number(rider_id, bundle=None):
    """Choose one latest rider design, independently of the displayed race era."""
    root, assets = _catalog(bundle)
    matches = [asset for asset in assets
               if asset["rider_id"] == rider_id and asset["category"] != "MotoE"]
    if not matches:
        return None
    asset = max(matches, key=lambda item: (
        item["season"], item["category"], item["number"], item["sha256"],
    ))
    return _verified(root, asset)


def list_numbers(rider_id, season=None, categories=None, bundle=None):
    root, assets = _catalog(bundle)
    requested = {canonical_category(category) for category in categories} if categories is not None else None
    groups = {}
    for asset in assets:
        if asset["rider_id"] != rider_id or (season is not None and asset["season"] != season):
            continue
        # MotoE is preserved in the bundle but is outside the app's race-data scope.
        if asset["category"] == "MotoE":
            continue
        category = canonical_category(asset["category"])
        if requested is not None and category not in requested:
            continue
        key = (asset["season"], category, asset["number"])
        groups.setdefault(key, []).append(asset)
    return [
        _verified(root, group[0])
        for _, group in sorted(groups.items(), reverse=True)
        if len({item["sha256"] for item in group}) == 1
    ]
