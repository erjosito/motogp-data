"""Read-only API and static host for the React dashboard preview."""

import logging
import math
import os
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

import pyodbc
from azure.core.exceptions import ClientAuthenticationError
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from sql_connection import connect_to_sql

app = FastAPI(title="MotoGP Preview API", docs_url="/api/docs", openapi_url="/api/openapi.json")
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


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/seasons")
def seasons():
    rows = query(f"""
        SELECT DISTINCT e.season_year AS season FROM events e
        JOIN sessions s ON s.event_id = e.event_id
        WHERE {TOP_CLASS} ORDER BY season DESC
    """)
    return [row["season"] for row in rows]


@app.get("/api/events")
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


@app.get("/api/events/{event_id}/sessions")
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


@app.get("/api/championship")
def championship(season: int = Query(ge=1949, le=3000)):
    rows = query(f"""
        SELECT s.session_id, s.session_type, s.session_label, s.session_date,
               e.event_id, e.short_name, e.date_end, r.rider_id,
               r.full_name AS rider, r.number, c.position, c.points,
               t.team_name AS team, t.constructor
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
    return build_championship(rows, season)


@app.get("/api/sessions/{session_id}/analysis")
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
               t.team_name AS team, t.constructor, c.total_laps, c.time_text,
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


web_dist = Path(os.environ.get("MOTOGP_WEB_DIST", Path(__file__).parent / "preview-web" / "dist"))
if web_dist.is_dir():
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
