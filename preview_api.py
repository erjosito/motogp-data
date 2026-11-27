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

app = FastAPI(title="MotoGP Preview API", docs_url="/api/docs", openapi_url="/api/openapi.json")
api = APIRouter()
logger = logging.getLogger(__name__)
TOP_CLASS = "(s.category LIKE N'MotoGP%' OR s.category = N'500cc')"
MARC_ID = "f55b433d-38b8-4d1d-bb3a-a709c82a0260"


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


def build_championship(rows: list[dict], season: int) -> dict:
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
        if MARC_ID in totals:
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
        "season": season, "standings": standings, "rounds": rounds, "comeback": comeback,
        "weekends": len(scoring_events),
        "gp_results": len(gp_events),
        "scoring_sessions": scoring_sessions,
    }


def season_story(data: dict) -> dict:
    season, standings = data["season"], data["standings"]
    if not standings:
        return {
            "headline": f"{season}: the story is still incomplete.",
            "accent": "The missing points matter.",
            "summary": "No usable championship standings are available. Session results are not a substitute for missing title points.",
            "metric_label": "SEASON", "metric": season, "metric_note": "Waiting for usable championship evidence",
            "context_url": None,
        }
    leader = standings[0]
    second = standings[1] if len(standings) > 1 else None
    gap = second["gap"] if second else 0
    name = leader["rider"]
    official = data["standings_source"] == "official"
    summary = (
        f"{name} is officially ranked first on {leader['points']:g} points"
        if official else f"{name} leads the imported results on {leader['points']:g} points"
    )
    if second:
        summary += f", {gap:g} ahead of {second['rider']}."
    else:
        summary += "."
    story = {
        "headline": f"{season}: {name}'s season.",
        "accent": "The points tell the story.",
        "summary": summary,
        "metric_label": "POINTS AT THE TOP", "metric": leader["points"],
        "metric_note": "Official final total" if official else "From imported GP + Sprint classifications",
        "context_url": None,
    }
    if official:
        story["summary"] += " Period scoring rules and official ranks are preserved; no race-by-race progression is inferred."
        if second and gap == 0:
            story.update(headline="Equal points.", accent="One official champion.",
                         metric_label="POINTS BETWEEN THE TOP TWO", metric=0,
                         metric_note="The official classification, not a recalculated tie-break, decides the order")
        elif second and gap <= 10:
            story.update(headline=f"{name}: a narrow crown.", accent=f"{gap:g} points made the difference.",
                         metric_label="OFFICIAL WINNING MARGIN", metric=gap,
                         metric_note=f"Points ahead of {second['rider']}")
        else:
            story.update(headline=f"{name} sets the standard.", accent=f"{season}, in the record books.")
        return story

    comeback = data["comeback"]
    if season == 2026 and comeback and comeback["verified_102"]:
        low = next(point for point in comeback["history"] if point["margin"] == -102)
        story.update(
            headline="102 points behind.", accent="A title fight rewritten.",
            summary=f"After {low['label']}, Marc Marquez was 102 points behind the strongest rival. "
                    f"His latest margin is {comeback['current_margin']:+g} points. The timeline includes every imported Sprint and Grand Prix.",
            metric_label="THE RECOVERY", metric=comeback["recovered"],
            metric_note="Points recovered since the lowest recorded margin",
        )
    elif season == 2025 and leader["rider_id"] == MARC_ID and leader["wins"] >= 10:
        story.update(
            headline="Back to the summit.", accent="Back to dominance.",
            summary=f"Marc Marquez tops the imported season with {leader['wins']} GP wins, "
                    f"{leader['points']:g} points and a {gap:g}-point advantage. "
                    "The results show dominance; MotoGP's account supplies the context of his long injury recovery.",
            metric_label="GRAND PRIX WINS", metric=leader["wins"],
            metric_note=f"Across {data['gp_results']} imported GP races",
            context_url="https://www.motogp.com/en/news/2025/11/27/the-marc-marquez-story-chapter-2-to-hell-and-back/822595",
        )
    elif second and second["wins"] > leader["wins"] and leader["wins"] <= data["gp_results"] / 4:
        story.update(
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
            story.update(headline="The last race changed everything.", accent=f"{name} took the top spot.",
                         summary=summary + " The leading rider in the imported points changed in the final recorded scoring session.",
                         metric_label="FINAL RECORDED MARGIN", metric=gap,
                         metric_note="Points ahead after the last imported session")
        elif deficit >= 25:
            story.update(headline=f"{name}: the long way back.", accent=f"From {deficit:g} behind to the top.",
                         summary=summary + f" Earlier in the imported timeline, the deficit reached {deficit:g} points.",
                         metric_label="POINTS RECOVERED", metric=deficit + gap,
                         metric_note="From the lowest margin to the latest imported result")
        elif data["gp_results"] and leader["wins"] >= data["gp_results"] / 2:
            story.update(headline=f"{name} takes control.", accent="Victory became the pattern.",
                         summary=summary + f" {leader['wins']} wins in {data['gp_results']} imported GP races underpin the advantage.",
                         metric_label="GRAND PRIX WINS", metric=leader["wins"],
                         metric_note=f"Across {data['gp_results']} imported GP races")
        elif second and gap <= 10:
            story.update(headline=f"{name}: every point mattered.", accent=f"Only {gap:g} points between them.",
                         metric_label="POINTS BETWEEN THE TOP TWO", metric=gap,
                         metric_note="From imported scoring classifications")
        elif data["gp_results"] and leader["podiums"] >= data["gp_results"] / 2:
            story.update(headline=f"{name}: always in the picture.", accent="Consistency wrote the story.",
                         summary=summary + f" {leader['podiums']} podiums are recorded across {data['gp_results']} GP races.",
                         metric_label="GRAND PRIX PODIUMS", metric=leader["podiums"],
                         metric_note=f"Across {data['gp_results']} imported GP races")
    return story


@api.get("/api/health")
def health():
    return {"status": "ok"}


@api.get("/api/seasons")
def seasons():
    rows = query(f"""
        SELECT DISTINCT e.season_year AS season FROM events e
        JOIN sessions s ON s.event_id = e.event_id
        WHERE {TOP_CLASS} ORDER BY season DESC
    """)
    return [row["season"] for row in rows]


@api.get("/api/events")
def events(season: int = Query(ge=1949, le=3000)):
    return query(f"""
        SELECT e.event_id, e.short_name, e.event_name, e.circuit_name,
               e.country_name, e.date_end
        FROM events e WHERE e.season_year = ? AND EXISTS (
            SELECT 1 FROM sessions s WHERE s.event_id = e.event_id AND {TOP_CLASS}
                AND s.status = 'FINISHED' AND (EXISTS (
                    SELECT 1 FROM classifications c WHERE c.session_id = s.session_id
                ) OR EXISTS (SELECT 1 FROM laps l WHERE l.session_id = s.session_id))
        ) ORDER BY e.date_end, e.short_name
    """, (season,))


@api.get("/api/events/{event_id}/sessions")
def sessions(event_id: str):
    if not query("SELECT event_id FROM events WHERE event_id = ?", (event_id,)):
        raise HTTPException(404, "Grand Prix not found.")
    return query(f"""
        SELECT s.session_id, s.session_type, s.session_label, s.session_date,
               s.weather, s.air_temp, s.ground_temp
        FROM sessions s WHERE s.event_id = ? AND {TOP_CLASS}
            AND s.status = 'FINISHED' AND (EXISTS (
                SELECT 1 FROM classifications c WHERE c.session_id = s.session_id
            ) OR EXISTS (SELECT 1 FROM laps l WHERE l.session_id = s.session_id))
        ORDER BY s.session_date, s.session_number
    """, (event_id,))


@api.get("/api/championship")
def championship(season: int = Query(ge=1949, le=3000)):
    if season < 1990:
        rows = query("""
            SELECT cs.position, cs.rider_id, r.full_name AS rider, r.number,
                   cs.points, cs.constructor_name AS constructor, cs.source_url
            FROM championship_standings cs JOIN riders r ON r.rider_id = cs.rider_id
            WHERE cs.season_year = ? AND cs.category = '500cc' AND cs.is_final = 1
            ORDER BY cs.position
        """, (season,))
        data = build_championship([], season)
        first_points = float(rows[0]["points"]) if rows else 0
        data["standings"] = [{
            **row, "points": float(row["points"]), "gap": first_points - float(row["points"]),
            "team": None, "wins": None, "podiums": None, "series": [],
        } for row in rows]
        data["standings_source"] = "official"
        data["story"] = season_story(data)
        return data
    rows = query(f"""
        SELECT s.session_id, s.session_type, s.session_label, s.session_date,
               e.event_id, e.short_name, e.date_end, r.rider_id,
               r.full_name AS rider, r.number, c.position, c.points,
               t.team_name AS team, COALESCE(c.constructor_name, t.constructor) AS constructor
        FROM classifications c JOIN riders r ON r.rider_id = c.rider_id
        JOIN sessions s ON s.session_id = c.session_id
        JOIN events e ON e.event_id = s.event_id
        LEFT JOIN teams t ON t.team_id = c.team_id AND t.season_year = e.season_year
        WHERE e.season_year = ? AND {TOP_CLASS}
              AND s.session_type IN ('RAC', 'SPR') AND s.status = 'FINISHED'
        ORDER BY e.date_end, s.session_date,
                 CASE WHEN s.session_type = 'SPR' THEN 0 ELSE 1 END,
                 s.session_id, c.position
    """, (season,))
    data = build_championship(rows, season)
    data["standings_source"] = "computed"
    data["story"] = season_story(data)
    return data


@api.get("/api/sessions/{session_id}/analysis")
def analysis(session_id: str):
    metadata = query(f"""
        SELECT s.session_id, s.session_label, s.session_type, s.session_date,
               s.weather, s.air_temp, s.ground_temp, e.event_id, e.short_name,
               e.event_name, e.circuit_name, e.country_name, e.season_year
        FROM sessions s JOIN events e ON e.event_id = s.event_id
        WHERE s.session_id = ? AND {TOP_CLASS}
    """, (session_id,))
    if not metadata:
        raise HTTPException(404, "Session not found.")
    results = query("""
        SELECT r.rider_id, r.full_name AS rider, r.number, c.position,
               t.team_name AS team, COALESCE(c.constructor_name, t.constructor) AS constructor, c.total_laps, c.time_text,
               c.gap_first, c.best_lap_time, c.top_speed, c.points, c.status
        FROM classifications c JOIN riders r ON r.rider_id = c.rider_id
        JOIN sessions s ON s.session_id = c.session_id
        JOIN events e ON e.event_id = s.event_id
        LEFT JOIN teams t ON t.team_id = c.team_id AND t.season_year = e.season_year
        WHERE c.session_id = ?
        ORDER BY CASE WHEN c.position IS NULL THEN 1 ELSE 0 END, c.position, r.full_name
    """, (session_id,))
    laps = query("""
        SELECT l.rider_id, r.full_name AS rider, r.number, l.lap_number,
               l.lap_time, l.t1, l.t2, l.t3, l.t4, l.speed_kmh,
               l.is_pit, l.run_number, l.front_tyre, l.rear_tyre
        FROM laps l JOIN riders r ON r.rider_id = l.rider_id
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
