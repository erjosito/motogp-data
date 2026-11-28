"""One allowlisted class/lineage contract for ingestion and both dashboards."""

CATEGORY_FAMILIES = {
    "premier": ("MotoGP", "500cc"),
    "intermediate": ("Moto2", "250cc"),
    "lightweight": ("Moto3", "125cc"),
    "350cc": ("350cc",),
    "50cc": ("50cc",),
    "80cc": ("80cc",),
}

CATEGORY_YEARS = {
    "500cc": (1949, 2001), "MotoGP": (2002, 3000),
    "250cc": (1949, 2009), "Moto2": (2010, 3000),
    "125cc": (1949, 2011), "Moto3": (2012, 3000),
    "350cc": (1949, 1982), "50cc": (1962, 1983), "80cc": (1984, 1989),
}


def normalize_category(value):
    return (value or "").replace("\u2122", "").strip().lower()


def category_sql(family="premier", column="category"):
    if family not in CATEGORY_FAMILIES:
        raise ValueError(f"Unsupported category family: {family}")
    if column not in ("category", "s.category", "cs.category"):
        raise ValueError("Unsupported category column")
    labels = ",".join(f"'{normalize_category(c)}'" for c in CATEGORY_FAMILIES[family])
    return f"LOWER(REPLACE(LTRIM(RTRIM({column})), N'\u2122', N'')) IN ({labels})"


def canonical_category(value):
    key = normalize_category(value)
    for category in CATEGORY_YEARS:
        if normalize_category(category) == key:
            return category
    raise ValueError(f"Unsupported Grand Prix class: {value}")


def qualifying_format(category, year):
    category = normalize_category(category)
    if category == "motogp" and year >= 2013:
        return 12, 2
    if category in ("moto2", "moto3") and year >= 2019:
        return 18, 4
    return None


def recorded_q2_poles(rows):
    """Count one rider's recorded Q2 wins, with observed-event coverage by class."""
    positions = {}
    for row in rows:
        if (row["session_type"] != "Q" or row["session_number"] != 2
                or row["session_status"] != "FINISHED"):
            continue
        format_spec = qualifying_format(row["category"], row["season_year"])
        if format_spec is None:
            continue
        position = row["position"]
        if (position is None or isinstance(position, bool)
                or not 1 <= position <= format_spec[0] or int(position) != position):
            continue
        key = (int(row["season_year"]), canonical_category(row["category"]), row["event_id"])
        positions.setdefault(key, set()).add(int(position))
    counts = {}
    for (year, category, _), observed in positions.items():
        if len(observed) != 1:
            continue
        season = counts.setdefault((year, category), {"gp_poles": 0, "gp_poles_q2_events": 0})
        season["gp_poles"] += observed == {1}
        season["gp_poles_q2_events"] += 1
    return counts


def official_points_inconsistent(position_points):
    """Flag source totals that cannot safely support rank-derived gaps/margins."""
    rows = sorted(position_points)
    return any(right[1] > left[1] for left, right in zip(rows, rows[1:]))
