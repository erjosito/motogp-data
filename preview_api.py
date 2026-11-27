"""Read-only API and static host for the React dashboard preview."""

import logging
import math
import os
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

import pyodbc
from azure.core.exceptions import ClientAuthenticationError
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from sql_connection import connect_to_sql
from category_scope import CATEGORY_FAMILIES, category_sql, normalize_category, official_points_inconsistent
from rider_profiles import read_enrichment

app = FastAPI(title="MotoGP Preview API", docs_url="/api/docs", openapi_url="/api/openapi.json")
api = APIRouter()
logger = logging.getLogger(__name__)
MARC_ID = "f55b433d-38b8-4d1d-bb3a-a709c82a0260"


def selected_class(category: str, column: str = "s.category") -> str:
    if category not in CATEGORY_FAMILIES:
        raise HTTPException(422, "Unsupported category family.")
    return category_sql(category, column)


@app.exception_handler(pyodbc.Error)
@app.exception_handler(ClientAuthenticationError)
@app.exception_handler(ValueError)
def database_error(request: Request, error: Exception):
    logger.error("Preview request failed on %s (%s)", request.url.path, type(error).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "The data service is unavailable. Please retry in a moment."},
    )


def query(sql: str, params: tuple = ()) -> list[dict]:
    with closing(connect_to_sql()) as connection, closing(connection.cursor()) as cursor:
        cursor.execute(sql, *params)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def seconds(value) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parts = value.strip().replace("'", ":").split(":")
        if len(parts) == 1:
            result = float(parts[0])
        elif len(parts) == 2:
            minutes, remainder = int(parts[0]), float(parts[1])
            if minutes < 0 or not 0 <= remainder < 60:
                return None
            result = minutes * 60 + remainder
        else:
            return None
        return result if math.isfinite(result) and result > 0 else None
    except ValueError:
        return None


def build_championship(rows: list[dict], season: int, category: str = "premier") -> dict:
    sessions = {}
    riders = {}
    finishes = defaultdict(Counter)
    for row in rows:
        sid, rid = row["session_id"], row["rider_id"]
        sessions.setdefault(sid, {
            "session_id": sid, "event_id": row["event_id"],
            "event": row["short_name"], "type": row["session_type"],
            "label": f'{row["short_name"]} / {row["session_label"]}',
            "date": row["session_date"] or row["date_end"], "rows": [],
        })["rows"].append(row)
        riders[rid] = {
            "rider_id": rid, "rider": row["rider"], "number": row["number"],
            "team": row["team"], "constructor": row["constructor"],
        }

    totals = {rid: 0.0 for rid in riders}
    series = {rid: [] for rid in riders}
    rounds, comeback_history, scoring_events, gp_events = [], [], set(), set()
    scoring_sessions = 0
    for session in sessions.values():
        if any(float(row["points"] or 0) > 0 for row in session["rows"]):
            scoring_sessions += 1
            scoring_events.add(session["event_id"])
            if session["type"] == "RAC":
                gp_events.add(session["event_id"])
                for row in session["rows"]:
                    if row["position"]:
                        finishes[row["rider_id"]][int(row["position"])] += 1
        rounds.append({key: value for key, value in session.items() if key != "rows"})
        for row in session["rows"]:
            totals[row["rider_id"]] += float(row["points"] or 0)
        for rid in riders:
            series[rid].append(totals[rid])
        if category == "premier" and MARC_ID in totals:
            rival = max((value for rid, value in totals.items() if rid != MARC_ID), default=0)
            comeback_history.append({
                **rounds[-1], "points": totals[MARC_ID], "margin": totals[MARC_ID] - rival,
            })

    ordered = sorted(
        totals,
        key=lambda rid: (
            -totals[rid], *(-finishes[rid][position] for position in range(1, 41)),
            riders[rid]["rider"],
        ),
    ) if scoring_sessions else []
    leader_points = totals[ordered[0]] if ordered else 0
    standings = [
        {
            **riders[rid], "position": index + 1, "points": totals[rid],
            "gap": leader_points - totals[rid], "wins": finishes[rid][1],
            "podiums": sum(finishes[rid][position] for position in [1, 2, 3]),
            "series": series[rid],
        }
        for index, rid in enumerate(ordered)
    ]
    comeback = None
    if comeback_history and scoring_sessions:
        low = min(comeback_history, key=lambda point: point["margin"])
        maximum_deficit = max(0, -low["margin"])
        comeback = {
            "rider_id": MARC_ID, "history": comeback_history, "low": low,
            "max_deficit": maximum_deficit,
            "current_margin": comeback_history[-1]["margin"],
            "recovered": comeback_history[-1]["margin"] + maximum_deficit,
            "verified_102": any(point["margin"] == -102 for point in comeback_history),
        }
    return {
        "season": season, "category": category, "standings": standings, "rounds": rounds, "comeback": comeback,
        "external_sources_used": any(row.get("source_kind", "official-api") != "official-api" for row in rows),
        "official_points_inconsistent": False, "points_warning": None,
        "weekends": len(scoring_events),
        "gp_results": len(gp_events),
        "scoring_sessions": scoring_sessions,
    }


def season_story(data: dict) -> dict:
    season, standings = data["season"], data["standings"]
    if not standings:
        return {
            "kind": "coverage",
            "headline": f"{season}: the story is still incomplete.",
            "accent": "The missing points matter.",
            "summary": (
                "Official final standings are unavailable for this season and category. "
                "Available race classifications, including external supplementation, are not a substitute "
                "and cannot establish a final championship or champion."
                if season < 1990 else
                "No usable championship standings are available. Session results are not a substitute for missing title points."
            ),
            "metric_label": "SEASON", "metric": season, "metric_note": "Waiting for usable championship evidence",
            "context_url": None,
        }
    leader = standings[0]
    second = standings[1] if len(standings) > 1 else None
    gap = second["gap"] if second else 0
    name = leader["rider"]
    official = data["standings_source"] == "official"
    final = data.get("is_final", official)
    if official and data.get("official_points_inconsistent"):
        return {
            "kind": "standings",
            "headline": f"{name}: officially ranked first.",
            "accent": "Official standings, in source order.",
            "summary": "Official positions and supplied scores are preserved unchanged.",
            "metric_label": "OFFICIAL RANK", "metric": leader["position"],
            "metric_note": "Official champion rank" if final else "Official rank to date; not a final result",
            "context_url": None,
        }
    summary = (
        f"{name} is officially ranked first on {leader['points']:g} points"
        if official else f"{name} leads the imported results on {leader['points']:g} points"
    )
    if second:
        summary += f", {gap:g} ahead of {second['rider']}."
    else:
        summary += "."
    story = {
        "kind": "standings",
        "headline": f"{season}: {name}'s season.",
        "accent": "The points tell the story.",
        "summary": summary,
        "metric_label": "POINTS AT THE TOP", "metric": leader["points"],
        "metric_note": ("Official final total" if final else "Official standings to date") if official else "From imported GP + Sprint classifications",
        "context_url": None,
    }
    marc_dominance = (data.get("category", "premier") == "premier" and season == 2025
                      and leader["rider_id"] == MARC_ID and (leader["wins"] or 0) >= 10)
    if official and final and not marc_dominance:
        story["summary"] += " Period scoring rules and official ranks are preserved; no race-by-race progression is inferred."
        if second and gap == 0:
            story.update(kind="tie-break", headline="Equal points.", accent="One official champion.",
                         metric_label="POINTS BETWEEN THE TOP TWO", metric=0,
                         metric_note="The official classification, not a recalculated tie-break, decides the order")
        elif second and gap <= 10:
            story.update(kind="close-finish", headline=f"{name}: a narrow crown.", accent=f"{gap:g} points made the difference.",
                         metric_label="OFFICIAL WINNING MARGIN", metric=gap,
                         metric_note=f"Points ahead of {second['rider']}")
        else:
            story.update(headline=f"{name} sets the standard.", accent=f"{season}, in the record books.")
        return story
    if official and not marc_dominance and not (data.get("category", "premier") == "premier" and season == 2026
                                               and data["comeback"] and data["comeback"]["verified_102"]):
        story["summary"] += " These are standings to date, not a final championship result."
        return story

    comeback = data["comeback"]
    if data.get("category", "premier") == "premier" and season == 2026 and comeback and comeback["verified_102"]:
        low = next(point for point in comeback["history"] if point["margin"] == -102)
        story.update(
            kind="comeback",
            headline="102 points behind.", accent="A title fight rewritten.",
            summary=f"After {low['label']}, Marc Marquez was 102 points behind the strongest rival. "
                    f"His latest margin is {comeback['current_margin']:+g} points. The timeline includes every imported Sprint and Grand Prix.",
            metric_label="THE RECOVERY", metric=comeback["recovered"],
            metric_note="Points recovered since the lowest recorded margin",
        )
        if official:
            story["summary"] += " The curve uses imported race points; the table preserves official standings to date, not a final championship."
    elif marc_dominance:
        story.update(
            kind="dominance",
            headline="Back to the summit.", accent="Back to dominance.",
            summary=f"Marc Marquez tops the imported season with {leader['wins']} GP wins, "
                    f"{leader['points']:g} points and a {gap:g}-point advantage. "
                    "The results show dominance; MotoGP's account supplies the context of his long injury recovery.",
            metric_label="GRAND PRIX WINS", metric=leader["wins"],
            metric_note=f"Across {data['gp_results']} imported GP races",
            context_url="https://www.motogp.com/en/news/2025/11/27/the-marc-marquez-story-chapter-2-to-hell-and-back/822595",
        )
        if official:
            story["summary"] += " Points and rank use the official standings; the win count uses imported GP classifications."
    elif second and second["wins"] > leader["wins"] and leader["wins"] <= data["gp_results"] / 4:
        story.update(
            kind="consistency",
            headline="Winning the title fight.", accent="Not just the races.",
            summary=f"{name} leads by {gap:g} points with {leader['wins']} GP wins. "
                    f"{second['rider']} won {second['wins']} GPs: winning more races did not mean scoring more points.",
            metric_label="POINTS BETWEEN THE TOP TWO", metric=gap,
            metric_note="Imported GP + Sprint points; not race wins alone",
        )
    else:
        margins = []
        for index, points in enumerate(leader["series"]):
            rival = max((rider["series"][index] for rider in standings[1:]), default=0)
            margins.append(points - rival)
        deficit = max(0, -min(margins, default=0))
        if len(margins) > 1 and margins[-2] < 0 <= margins[-1]:
            story.update(kind="late-surge", headline="The latest race changed the lead." if season == 2026 else "The last race changed everything.",
                         accent=f"{name} took the top spot.",
                         summary=summary + " The leading rider in the imported points changed in the latest recorded scoring session.",
                         metric_label="LATEST RECORDED MARGIN" if season == 2026 else "FINAL RECORDED MARGIN", metric=gap,
                         metric_note="Points ahead after the last imported session")
        elif deficit >= 25:
            story.update(kind="comeback", headline=f"{name}: the long way back.", accent=f"From {deficit:g} behind to the top.",
                         summary=summary + f" Earlier in the imported timeline, the deficit reached {deficit:g} points.",
                         metric_label="POINTS RECOVERED", metric=deficit + gap,
                         metric_note="From the lowest margin to the latest imported result")
        elif data["gp_results"] and leader["wins"] >= data["gp_results"] / 2:
            story.update(kind="dominance", headline=f"{name} takes control.", accent="Victory became the pattern.",
                         summary=summary + f" {leader['wins']} wins in {data['gp_results']} imported GP races underpin the advantage.",
                         metric_label="GRAND PRIX WINS", metric=leader["wins"],
                         metric_note=f"Across {data['gp_results']} imported GP races")
        elif second and gap <= 10:
            story.update(kind="close-finish", headline=f"{name}: every point mattered.", accent=f"Only {gap:g} points between them.",
                         metric_label="POINTS BETWEEN THE TOP TWO", metric=gap,
                         metric_note="From imported scoring classifications")
        elif data["gp_results"] and leader["podiums"] >= data["gp_results"] / 2:
            story.update(kind="consistency", headline=f"{name}: always in the picture.", accent="Consistency wrote the story.",
                         summary=summary + f" {leader['podiums']} podiums are recorded across {data['gp_results']} GP races.",
                         metric_label="GRAND PRIX PODIUMS", metric=leader["podiums"],
                         metric_note=f"Across {data['gp_results']} imported GP races")
    return story


@api.get("/api/health")
def health():
    return {"status": "ok"}


@api.get("/api/seasons")
def seasons(category: str = "premier"):
    scope = selected_class(category)
    standings_scope = selected_class(category, "cs.category")
    rows = query(f"""
        SELECT e.season_year AS season FROM events e
        JOIN sessions s ON s.event_id = e.event_id
        WHERE {scope}
        UNION
        SELECT cs.season_year AS season FROM championship_standings cs
        WHERE {standings_scope}
        ORDER BY season DESC
    """)
    return [row["season"] for row in rows]


def rider_category(value: str) -> str | None:
    key = normalize_category(value)
    return next((family for family, labels in CATEGORY_FAMILIES.items()
                 if key in [normalize_category(label) for label in labels]), None)


def build_rider_profile(rider: dict, races: list[dict], standings: list[dict]) -> dict:
    seasons_by_class = {}
    venues = {}
    for race in races:
        family = rider_category(race["category"])
        if family is None:
            continue
        key = (race["season"], family)
        season = seasons_by_class.setdefault(key, {
            "season": key[0], "category": family, "gp_appearances": 0, "gp_wins": 0,
            "gp_podiums": 0, "sprint_wins": 0, "sprint_appearances": 0,
            "position": None, "points": None, "is_final": False, "source_url": None,
        })
        position = race["position"]
        if race["session_type"] == "SPR":
            season["sprint_appearances"] += 1
            season["sprint_wins"] += position == 1
            continue
        season["gp_appearances"] += 1
        season["gp_wins"] += position == 1
        season["gp_podiums"] += position is not None and 1 <= position <= 3
        venue_name = race["circuit_name"] or race["event_name"]
        venue = venues.setdefault(venue_name, {"venue": venue_name, "appearances": 0, "wins": 0, "podiums": 0})
        venue["appearances"] += 1
        venue["wins"] += position == 1
        venue["podiums"] += position is not None and 1 <= position <= 3
    for row in standings:
        family = rider_category(row["category"])
        if family is None:
            continue
        key = (row["season"], family)
        season = seasons_by_class.setdefault(key, {
            "season": key[0], "category": family, "gp_appearances": 0, "gp_wins": 0,
            "gp_podiums": 0, "sprint_wins": 0, "sprint_appearances": 0,
            "position": None, "points": None, "is_final": False, "source_url": None,
        })
        if season["is_final"] and not row["is_final"]:
            continue
        season.update(position=row["position"], points=float(row["points"]),
                      is_final=bool(row["is_final"]), source_url=row["source_url"])
    career = sorted(seasons_by_class.values(), key=lambda row: (row["season"], row["category"]))
    totals = {key: sum(row[key] for row in career)
              for key in ["gp_appearances", "gp_wins", "gp_podiums", "sprint_wins", "sprint_appearances"]}
    titles = [row for row in career if row["is_final"] and row["position"] == 1]
    best = max((row for row in career if row["gp_appearances"]), key=lambda row: (row["gp_wins"], row["gp_podiums"], row["season"]), default=None)
    is_marc = rider["rider_id"] == MARC_ID
    name = rider["rider"].split(" ")[0]
    headline = "The art of coming back." if is_marc else (
        f"{len(titles)} recorded titles. One remarkable rider." if titles and all(row["position"] is not None for row in career) else
        f"{name}, at the sharp end." if totals["gp_wins"] else f"{name}, beyond the standings.")
    if best and best["gp_wins"]:
        summary = f"{best['gp_wins']} recorded GP wins in {best['season']}: the strongest winning season in this rider's archive."
    elif titles:
        summary = "A career defined by official championship-winning seasons."
    else:
        summary = "The seasons, results and championship positions that tell this rider's story."
    return {
        "rider": rider, "headline": headline, "summary": summary, "totals": {**totals, "titles": len(titles)},
        "seasons": career, "titles": titles, "best_season": best,
        "venues": sorted(venues.values(), key=lambda row: (-row["wins"], -row["podiums"], -row["appearances"], row["venue"])),
        "first_season": career[0]["season"] if career else None,
        "latest_season": career[-1]["season"] if career else None,
    }


@api.get("/api/riders")
def rider_directory():
    scope = " OR ".join(f"({selected_class(family)})" for family in CATEGORY_FAMILIES)
    standings_scope = " OR ".join(f"({selected_class(family, 'cs.category')})" for family in CATEGORY_FAMILIES)
    return query(f"""
        WITH active_riders AS (
            SELECT cs.rider_id FROM championship_standings cs WHERE {standings_scope}
            UNION
            SELECT c.rider_id FROM dbo.vw_effective_classifications c
            JOIN sessions s ON s.session_id = c.session_id
            JOIN events e ON e.event_id = s.event_id
            WHERE s.status = 'FINISHED' AND s.session_type IN ('RAC','SPR') AND ({scope})
                AND (e.season_year < 1990 OR EXISTS (
                    SELECT 1 FROM dbo.vw_effective_classifications scored
                    WHERE scored.session_id = s.session_id AND scored.points > 0
                ))
        )
        SELECT r.rider_id, r.full_name AS rider, r.number FROM riders r
        JOIN active_riders a ON a.rider_id = r.rider_id
        ORDER BY r.full_name, r.rider_id
    """)


@api.get("/api/riders/{rider_id}")
def rider_profile(rider_id: str):
    riders = query("SELECT rider_id, full_name AS rider, number FROM riders WHERE rider_id = ?", (rider_id,))
    if not riders:
        raise HTTPException(404, "Rider not found.")
    races = query("""
        SELECT e.season_year AS season, s.category, s.session_type, c.position,
               e.circuit_name, e.event_name
        FROM dbo.vw_effective_classifications c
        JOIN sessions s ON s.session_id = c.session_id JOIN events e ON e.event_id = s.event_id
        WHERE c.rider_id = ? AND s.status = 'FINISHED' AND s.session_type IN ('RAC','SPR')
            AND (e.season_year < 1990 OR EXISTS (
                SELECT 1 FROM dbo.vw_effective_classifications scored
                WHERE scored.session_id = s.session_id AND scored.points > 0
            ))
        ORDER BY e.season_year, s.category, s.session_id
    """, (rider_id,))
    standings = query("""
        SELECT cs.season_year AS season, cs.category, cs.position, cs.points, cs.is_final, cs.source_url
        FROM championship_standings cs WHERE cs.rider_id = ?
        ORDER BY cs.season_year, cs.category, cs.is_final
    """, (rider_id,))
    profile = build_rider_profile(riders[0], races, standings)
    if not profile["seasons"]:
        raise HTTPException(404, "No Grand Prix career evidence is available for this rider.")
    return profile


@api.get("/api/riders/{rider_id}/enrichment")
def rider_enrichment(rider_id: str):
    return read_enrichment(rider_id)


@api.get("/api/events")
def events(season: int = Query(ge=1949, le=3000), category: str = "premier"):
    scope = selected_class(category)
    return query(f"""
        SELECT e.event_id, e.short_name, e.event_name, e.circuit_name,
               e.country_name, e.date_end
        FROM events e WHERE e.season_year = ? AND EXISTS (
            SELECT 1 FROM sessions s WHERE s.event_id = e.event_id AND {scope}
                AND s.status = 'FINISHED' AND (EXISTS (
                    SELECT 1 FROM dbo.vw_effective_classifications c WHERE c.session_id = s.session_id
                ) OR EXISTS (SELECT 1 FROM laps l WHERE l.session_id = s.session_id))
        ) ORDER BY e.date_end, e.short_name
    """, (season,))


@api.get("/api/events/{event_id}/sessions")
def sessions(event_id: str, category: str = "premier"):
    scope = selected_class(category)
    if not query("SELECT event_id FROM events WHERE event_id = ?", (event_id,)):
        raise HTTPException(404, "Grand Prix not found.")
    return query(f"""
        SELECT s.session_id, s.session_type, s.session_label, s.session_date,
               s.weather, s.air_temp, s.ground_temp
        FROM sessions s WHERE s.event_id = ? AND {scope}
            AND s.status = 'FINISHED' AND (EXISTS (
                SELECT 1 FROM dbo.vw_effective_classifications c WHERE c.session_id = s.session_id
            ) OR EXISTS (SELECT 1 FROM laps l WHERE l.session_id = s.session_id))
        ORDER BY s.session_date, s.session_number
    """, (event_id,))


@api.get("/api/championship")
def championship(season: int = Query(ge=1949, le=3000), category: str = "premier"):
    scope = selected_class(category)
    standings_scope = selected_class(category, "cs.category")
    official_rows = query(f"""
            SELECT cs.position, cs.rider_id, r.full_name AS rider, r.number,
                   cs.points, cs.constructor_name AS constructor, cs.source_url, cs.is_final
            FROM championship_standings cs JOIN riders r ON r.rider_id = cs.rider_id
            WHERE cs.season_year = ? AND {standings_scope}
                  {"AND cs.is_final = 1" if season < 1990 else ""}
            ORDER BY cs.position
        """, (season,))
    inconsistent = official_points_inconsistent([
        (row["position"], float(row["points"])) for row in official_rows
    ])
    points_warning = (
        "Supplied official point totals require source verification: points do not follow official ranks. "
        "Period scoring or source discrepancies may explain this."
        if inconsistent else None
    )
    if season < 1990:
        data = build_championship([], season, category)
        first_points = float(official_rows[0]["points"]) if official_rows else 0
        data["standings"] = [{
            **row, "points": float(row["points"]),
            "gap": None if inconsistent else first_points - float(row["points"]),
            "team": None, "wins": None, "podiums": None, "series": [],
        } for row in official_rows]
        data["standings_source"] = "official"
        data["official_points_inconsistent"] = inconsistent
        data["points_warning"] = points_warning
        data["is_final"] = bool(official_rows) and all(row.get("is_final", season < 1990) for row in official_rows)
        data["story"] = season_story(data)
        if not data["standings"]:
            data["coverage"] = championship_coverage(season, category)
        return data
    rows = query(f"""
        SELECT s.session_id, s.session_type, s.session_label, s.session_date,
               e.event_id, e.short_name, e.date_end, r.rider_id,
               r.full_name AS rider, COALESCE(c.rider_number, r.number) AS number, c.position, c.points, c.source_kind,
               t.team_name AS team, COALESCE(c.constructor_name, t.constructor) AS constructor
        FROM dbo.vw_effective_classifications c JOIN riders r ON r.rider_id = c.rider_id
        JOIN sessions s ON s.session_id = c.session_id
        JOIN events e ON e.event_id = s.event_id
        LEFT JOIN teams t ON t.team_id = c.team_id AND t.season_year = e.season_year
        WHERE e.season_year = ? AND {scope}
              AND s.session_type IN ('RAC', 'SPR') AND s.status = 'FINISHED'
        ORDER BY e.date_end, s.session_date,
                 CASE WHEN s.session_type = 'SPR' THEN 0 ELSE 1 END,
                 s.session_id, c.position
    """, (season,))
    data = build_championship(rows, season, category)
    data["standings_source"] = "computed"
    data["is_final"] = False
    if official_rows:
        first_points = float(official_rows[0]["points"])
        imported = {row["rider_id"]: row for row in data["standings"]}
        data["standings"] = [{
            **row, "points": float(row["points"]),
            "gap": None if inconsistent else first_points - float(row["points"]),
            "team": None,
            "number": imported.get(row["rider_id"], {}).get("number", row["number"]),
            "wins": imported.get(row["rider_id"], {}).get("wins"),
            "podiums": imported.get(row["rider_id"], {}).get("podiums"),
            "series": [],
        } for row in official_rows]
        data["standings_source"] = "official"
        data["is_final"] = all(row["is_final"] for row in official_rows)
        data["official_points_inconsistent"] = inconsistent
        data["points_warning"] = points_warning
        if inconsistent:
            data["comeback"] = None
    data["story"] = season_story(data)
    if not data["standings"]:
        data["coverage"] = championship_coverage(season, category)
    return data


def championship_coverage(season: int, category: str) -> dict:
    scope = selected_class(category)
    return query(f"""
        WITH scoped_sessions AS (
            SELECT s.session_id FROM sessions s
            JOIN events e ON e.event_id = s.event_id
            WHERE e.season_year = ? AND {scope} AND s.status = 'FINISHED'
        )
        SELECT
            (SELECT COUNT(*) FROM scoped_sessions) AS sessions,
            (SELECT COUNT(*) FROM scoped_sessions s WHERE EXISTS (
                SELECT 1 FROM dbo.vw_effective_classifications c WHERE c.session_id = s.session_id
            )) AS classified_sessions,
            (SELECT COUNT(*) FROM dbo.vw_effective_classifications c
             JOIN scoped_sessions s ON s.session_id = c.session_id) AS classification_rows,
            (SELECT COUNT(*) FROM laps l
             JOIN scoped_sessions s ON s.session_id = l.session_id) AS lap_rows
    """, (season,))[0]


@api.get("/api/sessions/{session_id}/analysis")
def analysis(session_id: str, category: str = "premier"):
    scope = selected_class(category)
    metadata = query(f"""
        SELECT s.session_id, s.session_label, s.session_type, s.session_date,
               s.weather, s.air_temp, s.ground_temp, e.event_id, e.short_name,
               e.event_name, e.circuit_name, e.country_name, e.season_year, s.category
        FROM sessions s JOIN events e ON e.event_id = s.event_id
        WHERE s.session_id = ? AND {scope}
    """, (session_id,))
    if not metadata:
        raise HTTPException(404, "Session not found.")
    results = query("""
        SELECT c.*, r.full_name AS rider, COALESCE(c.rider_number, r.number) AS number,
               t.team_name AS team, COALESCE(c.constructor_name, t.constructor) AS constructor
        FROM dbo.vw_effective_classifications c JOIN riders r ON r.rider_id = c.rider_id
        JOIN sessions s ON s.session_id = c.session_id
        JOIN events e ON e.event_id = s.event_id
        LEFT JOIN teams t ON t.team_id = c.team_id AND t.season_year = e.season_year
        WHERE c.session_id = ?
        ORDER BY CASE WHEN c.position IS NULL THEN 1 ELSE 0 END, c.position, r.full_name
    """, (session_id,))
    laps = query("""
        SELECT l.rider_id, r.full_name AS rider, COALESCE(c.rider_number, r.number) AS number, l.lap_number,
               l.lap_time, l.t1, l.t2, l.t3, l.t4, l.speed_kmh,
               l.is_pit, l.run_number, l.front_tyre, l.rear_tyre
        FROM laps l JOIN riders r ON r.rider_id = l.rider_id
        LEFT JOIN dbo.vw_effective_classifications c ON c.session_id = l.session_id AND c.rider_id = l.rider_id
        WHERE l.session_id = ? ORDER BY r.full_name, l.lap_number
    """, (session_id,))
    for lap in laps:
        lap["lap_seconds"] = seconds(lap["lap_time"])
        lap["sectors"] = [seconds(lap[key]) for key in ["t1", "t2", "t3", "t4"]]
    for result in results:
        result["best_lap_seconds"] = seconds(result["best_lap_time"])
    return {"session": metadata[0], "results": results, "laps": laps}


app.include_router(api)
app.include_router(api, prefix="/paddock")


@app.get("/paddock", include_in_schema=False)
def paddock_redirect(request: Request):
    suffix = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(f"/paddock/{suffix}", status_code=308)


web_dist = Path(os.environ.get("MOTOGP_WEB_DIST", Path(__file__).parent / "preview-web" / "dist"))
if web_dist.is_dir():
    app.mount("/paddock", StaticFiles(directory=web_dist, html=True), name="paddock")
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
