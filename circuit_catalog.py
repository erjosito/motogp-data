"""Sourced circuit facts and outlines, matched by physical circuit names."""

import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path


def normalized_name(value):
    return "".join(
        char for char in unicodedata.normalize("NFKD", value).casefold()
        if char.isalnum() and not unicodedata.combining(char)
    )


@lru_cache(maxsize=1)
def catalog():
    records = json.loads(
        Path(__file__).with_name("circuit_catalog.json").read_text(encoding="utf-8")
    )["circuits"]
    aliases = {}
    for record in records:
        for name in [record["name"], *record["aliases"]]:
            key = normalized_name(name)
            if key in aliases and aliases[key]["id"] != record["id"]:
                raise ValueError(f"Ambiguous circuit alias: {name}")
            aliases[key] = record
    return aliases


def circuit_details(name):
    return catalog().get(normalized_name(name))


def circuit_key(name, place):
    details = circuit_details(name)
    return details["id"] if details else f"{normalized_name(name)}:{normalized_name(place)}"


def projected_outline(outline):
    """Project longitude/latitude locally so the diagram preserves proportions."""
    if len(outline) < 4 or outline[0] != outline[-1] or any(
        len(point) != 2 or not all(math.isfinite(value) for value in point)
        or not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90
        for point in outline
    ):
        raise ValueError("Circuit outline requires a closed lap of valid longitude/latitude points")
    longitude, latitude = zip(*outline)
    scale = math.cos(math.radians(sum(latitude) / len(latitude)))
    return (
        [(value - longitude[0]) * scale for value in longitude],
        [value - latitude[0] for value in latitude],
    )
