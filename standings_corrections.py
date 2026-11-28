"""Independently sourced corrections; never modify the official snapshot."""

CORRECTIONS = {
    (1970, "350cc"): {
        "source_url": "https://en.wikipedia.org/wiki/1970_Grand_Prix_motorcycle_racing_season#350cc_final_standings",
        "corroborating_url": "https://www.lequipe.fr/Moto/1970/moto-350cc-classement.html",
        "note": (
            "1970 350cc: the official source reports 9 and 28 points for Agostini and "
            "Carruthers; independent historical standings report 90 and 58 counted points. "
            "Only the best six races counted. Other official entries remain unverified."
        ),
        "rows": (
            ("ea0101ee-6b38-4d39-a466-fa83d2e1b36f", 1, 9, 90),
            ("b3668951-07a4-43f1-962a-8c4fde9dfe7a", 2, 28, 58),
        ),
    },
}


def corrected_standings(rows, season, family):
    """Apply a complete reviewed set only to the exact final official snapshot."""
    correction = CORRECTIONS.get((season, family))
    if not correction:
        return rows, None
    by_id = {row["rider_id"]: row for row in rows}
    if len(by_id) != len(rows):
        return rows, None
    for rider_id, rank, raw, _ in correction["rows"]:
        row = by_id.get(rider_id)
        if (
            not row or not row.get("is_final") or row["position"] != rank
            or row["points"] != raw
        ):
            return rows, None
    values = {rider_id: corrected for rider_id, _, _, corrected in correction["rows"]}
    output = []
    for row in rows:
        row = dict(row)
        if row["rider_id"] in values:
            row["source_points"] = row["points"]
            row["points"] = values[row["rider_id"]]
        output.append(row)
    return output, {key: correction[key] for key in ("source_url", "corroborating_url", "note")}
