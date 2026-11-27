"""Shared contracts for archive metrics; absent evidence stays unavailable."""

import numpy as np
import pandas as pd

from category_scope import CATEGORY_FAMILIES, canonical_category, normalize_category


CATEGORY_ORDER = [
    label for labels in CATEGORY_FAMILIES.values() for label in reversed(labels)
]


def complete_points(values):
    return values.sum(min_count=len(values)) if len(values) else np.nan


def nominal_maximum(year, races, sprints=0, missing=0):
    year, races, sprints, missing = np.broadcast_arrays(
        *[np.asarray(value, dtype=float) for value in (year, races, sprints, missing)]
    )
    maximum = races * 25 + sprints * 12
    supported = (
        (year >= 1993) & (missing == 0) & (races >= 0) & (sprints >= 0)
        & ((sprints == 0) | (year >= 2023)) & (maximum > 0)
    )
    return np.where(supported, maximum, np.nan)


def points_efficiency(points, maximum):
    points, maximum = np.broadcast_arrays(
        np.asarray(points, dtype=float), np.asarray(maximum, dtype=float)
    )
    return np.round(np.divide(
        points * 100, maximum, out=np.full(points.shape, np.nan),
        where=np.isfinite(maximum) & (maximum > 0) & (points >= 0) & (points <= maximum),
    ), 1)


def career_seasons(races, finals):
    keys = ["season_year", "category", "rider_id"]
    races = races.copy()
    races["category"] = races["category"].map(canonical_category)
    recorded = races.groupby(keys).agg(
        races=("session_id", "nunique"), wins=("position", lambda values: values.eq(1).sum()),
        podiums=("position", lambda values: values.isin([1, 2, 3]).sum()),
    ).reset_index()
    official = finals[finals["is_final"].eq(True)].copy()
    official["category"] = official["category"].map(canonical_category)
    result = recorded.merge(
        official[[*keys, "position", "source_url"]], on=keys, how="outer", validate="one_to_one"
    )
    for column in ["races", "wins", "podiums"]:
        result[column] = pd.to_numeric(result[column]).fillna(0).astype(int)
    return result.sort_values(["season_year", "category"])


def constructor_eras(rows, top_n, unknown, others):
    rows = rows.copy()
    rows["category"] = rows["category"].map(canonical_category)
    rows["constructor"] = rows["constructor"].replace(r"^\s*$", np.nan, regex=True).fillna(unknown)
    rows["decade"] = rows["season_year"] // 10 * 10
    kept = []
    for _, group in rows.groupby("category"):
        leaders = group.groupby("constructor")["wins"].sum().nlargest(top_n).index
        group = group.copy()
        group["constructor"] = group["constructor"].where(
            group["constructor"].isin(leaders) | group["constructor"].eq(unknown), others
        )
        kept.append(group)
    if not kept:
        return pd.DataFrame(columns=["category", "decade", "constructor", "wins", "share"])
    result = pd.concat(kept).groupby(["category", "decade", "constructor"])["wins"].sum().reset_index()
    result["share"] = result["wins"] / result.groupby(["category", "decade"])["wins"].transform("sum") * 100
    return result


def archive_availability(rows, metric):
    rows = rows.copy()
    rows["category"] = rows["category"].map(canonical_category)
    counts = rows.pivot_table(index="category", columns="season_year", values=metric,
                              aggfunc="sum", fill_value=0)
    if counts.empty:
        return counts
    return counts.reindex(
        index=[category for category in CATEGORY_ORDER if category in counts.index],
        columns=range(int(counts.columns.min()), int(counts.columns.max()) + 1), fill_value=0,
    )


def qualifying_format(category, year):
    category = normalize_category(category)
    if category == "motogp" and year >= 2013:
        return 12, 2
    if category in ("moto2", "moto3") and year >= 2019:
        return 18, 4
    return None


def qualifying_proxy(qualifying, races):
    """Keep complete two-stage qualifying orders, not inferred starting grids."""
    columns = [*races.columns, "grid_pos"]
    if qualifying.empty or races.empty:
        return pd.DataFrame(columns=columns)
    qualifying = qualifying.copy()
    races = races.copy()
    for frame in (qualifying, races):
        frame["category"] = frame["category"].map(normalize_category)
    prepared = []
    for (event_id, category), rows in qualifying.groupby(["event_id", "category"]):
        format_spec = qualifying_format(category, rows["season_year"].iloc[0])
        if format_spec is None:
            continue
        q2_size, promoted = format_spec
        q1, q2 = (rows[rows["session_number"].eq(stage)] for stage in (1, 2))
        if q1.empty or len(q2) != q2_size:
            continue
        if any(
            stage["position"].isna().any()
            or stage["rider_id"].duplicated().any()
            or sorted(stage["position"]) != list(range(1, len(stage) + 1))
            for stage in (q1, q2)
        ):
            continue
        advancing = set(q1.loc[q1["position"] <= promoted, "rider_id"])
        if set(q1["rider_id"]) & set(q2["rider_id"]) != advancing:
            continue
        tail = q1[~q1["rider_id"].isin(q2["rider_id"])].sort_values("position").copy()
        tail["grid_pos"] = np.arange(q2_size + 1, q2_size + 1 + len(tail))
        front = q2.assign(grid_pos=q2["position"])
        order = pd.concat([front, tail])[["rider_id", "grid_pos"]]
        event_races = races[races["event_id"].eq(event_id) & races["category"].eq(category)]
        for _, race in event_races.groupby("session_id"):
            starters = race[~race["status"].eq("NOTSTARTED")]
            if (
                starters.empty or starters["rider_id"].duplicated().any()
                or not starters["status"].isin([
                    "INSTND", "FINISHEDTHRUPITS", "OUTSTND", "NOTFINISHFIRST", "DISQUALIFIED"
                ]).all()
                or not set(starters["rider_id"]).issubset(set(order["rider_id"]))
                or starters.loc[starters["status"].isin(["INSTND", "FINISHEDTHRUPITS"]),
                                "finish_pos"].isna().any()
            ):
                continue
            prepared.append(starters.merge(order, on="rider_id", validate="one_to_one"))
    return pd.concat(prepared, ignore_index=True) if prepared else pd.DataFrame(columns=columns)
