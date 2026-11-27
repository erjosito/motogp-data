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


def official_points_inconsistent(position_points):
    """Flag source totals that cannot safely support rank-derived gaps/margins."""
    rows = sorted(position_points)
    return any(right[1] > left[1] for left, right in zip(rows, rows[1:]))
