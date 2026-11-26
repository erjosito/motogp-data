#!/usr/bin/env python3
"""
MotoGP Data Dashboard — Streamlit app

Run locally:  streamlit run dashboard.py
"""

import warnings

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import pyodbc
import pandas as pd
import streamlit as st
from azure.core.exceptions import ClientAuthenticationError

from sql_connection import connect_to_sql

warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_conn = None


def get_conn():
    global _conn
    try:
        if _conn is None:
            _conn = connect_to_sql()
            return _conn
        try:
            _conn.execute("SELECT 1")
            return _conn
        except Exception:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = connect_to_sql()
            return _conn
    except ClientAuthenticationError:
        st.error(
            "Cannot authenticate to Azure SQL. In Azure, enable the app's managed "
            "identity and grant it database access. Locally, run az login with an "
            "authorized Microsoft Entra account."
        )
        st.stop()
    except ValueError as e:
        st.error(f"Invalid Azure SQL configuration: {e}")
        st.stop()
    except pyodbc.OperationalError as e:
        err = str(e)
        if "not allowed to access the server" in err:
            st.error(
                "⛔ **Database connection blocked** — your IP address is not allowed. "
                "Please ask an administrator to update the Azure SQL firewall rule."
            )
        elif "Login timeout" in err or "Unable to complete login" in err:
            st.error(
                "⏳ **Database is waking up** — the serverless database is resuming from auto-pause. "
                "Please wait 15-30 seconds and refresh the page."
            )
        else:
            st.error(f"❌ **Cannot connect to database**: {err[:200]}")
        st.stop()


def q(sql, params=None):
    try:
        return pd.read_sql(sql, get_conn(), params=params)
    except pyodbc.OperationalError as e:
        err = str(e)
        if "not allowed to access the server" in err:
            st.error(
                "⛔ **Database connection blocked** — your IP address is not allowed. "
                "Please ask an administrator to update the Azure SQL firewall rule."
            )
        elif "Login timeout" in err or "Unable to complete login" in err:
            st.error(
                "⏳ **Database is waking up** — the serverless database is resuming from auto-pause. "
                "Please wait 15-30 seconds and refresh the page."
            )
        elif "Communication link failure" in err:
            st.error(
                "🔌 **Database connection lost** — the connection was interrupted "
                "(possibly due to network change or sleep). Please refresh the page."
            )
        else:
            st.error(f"❌ **Database error**: {err[:200]}")
        st.stop()
    except pyodbc.ProgrammingError as e:
        st.error(f"❌ **Query error**: {str(e)[:200]}")
        st.stop()
    except Exception as e:
        st.error(f"❌ **Unexpected error**: {str(e)[:200]}")
        st.stop()


PREMIER_CATEGORY = "LOWER(REPLACE(LTRIM(RTRIM(category)), N'™', N'')) IN ('motogp', '500cc')"


def premier_q(sql, params=None):
    """Scope every reference to sessions, including subqueries, to the premier class."""
    return q(
        f"WITH sessions AS (SELECT * FROM dbo.sessions WHERE {PREMIER_CATEGORY})\n{sql}",
        params,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def lap_to_sec(t) -> float | None:
    if not t or not isinstance(t, str):
        return None
    t = t.strip().replace("'", ":")
    try:
        if ":" in t:
            p = t.split(":")
            return float(p[0]) * 60 + float(p[1])
        return float(t)
    except (ValueError, IndexError):
        return None


def fmt(secs) -> str:
    if secs is None or (isinstance(secs, float) and np.isnan(secs)):
        return ""
    m = int(secs // 60)
    s = secs - m * 60
    return f"{m}:{s:06.3f}" if m > 0 else f"{s:.3f}"


def green_red_style(val, vmin, vmax):
    if pd.isna(val):
        return ""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if np.isnan(v):
        return ""
    ratio = (v - vmin) / (vmax - vmin) if vmax != vmin else 0.5
    ratio = max(0, min(1, ratio))
    if ratio < 0.5:
        r, g = int(255 * ratio * 2), 200
    else:
        r, g = 255, int(200 * (1 - (ratio - 0.5) * 2))
    return f"background-color: rgba({r},{g},50,0.6); color: black; font-weight: bold"


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="MotoGP Race Desk", page_icon="🏍", layout="wide")

st.markdown("""
<style>
    [data-testid="stMainBlockContainer"] {
        max-width: 1600px;
        padding-top: 4rem;
        padding-bottom: 3rem;
    }
    h1 { letter-spacing: -0.045em; }
    h2, h3 { letter-spacing: -0.025em; }
    [data-testid="stSidebar"] { border-right: 1px solid #e3e7ef; }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e3e7ef;
        border-radius: 12px;
        padding: 1rem;
    }
    [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
    [data-testid="stPlotlyChart"] {
        background: #ffffff;
        border: 1px solid #e3e7ef;
        border-radius: 12px;
        overflow: hidden;
    }
    @media (max-width: 768px) {
        [data-testid="stMainBlockContainer"] {
            padding: 4rem 1rem 2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

pio.templates["motogp"] = go.layout.Template(layout=go.Layout(
    font=dict(family="Arial, sans-serif", size=13, color="#172033"),
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    colorway=["#c8102e", "#2563eb", "#0f766e", "#9333ea", "#d97706",
              "#0284c7", "#be185d", "#475569", "#65a30d", "#7c3aed"],
    xaxis=dict(gridcolor="#edf0f5", zeroline=False, automargin=True),
    yaxis=dict(gridcolor="#edf0f5", zeroline=False, automargin=True),
    hoverlabel=dict(bgcolor="#ffffff", font_size=13),
    margin=dict(l=24, r=24, t=64, b=48),
))
pio.templates.default = "plotly_white+motogp"
px.defaults.template = "plotly_white+motogp"

# ---------------------------------------------------------------------------
# Language selector + translation
# ---------------------------------------------------------------------------
from translations import get_translator

LANG_OPTIONS = {"🇬🇧 English": "en", "🇪🇸 Español": "es", "🇮🇹 Italiano": "it"}
st.sidebar.markdown("## MotoGP")
lang_sel = st.sidebar.selectbox(
    "Language / Idioma / Lingua", list(LANG_OPTIONS.keys()), key="language"
)
lang = LANG_OPTIONS[lang_sel]
t = get_translator(lang)

st.title(t("app_title"))
st.caption(t("app_tagline"))

# ---------------------------------------------------------------------------
# Sidebar — visualization picker
# ---------------------------------------------------------------------------

NAV_GROUPS = {
    "nav_overview": ["viz_home"],
    "nav_race": ["viz_classification", "viz_rhythm", "viz_laptimes", "viz_position",
                 "viz_distribution", "viz_sectors", "viz_tyredeg", "viz_speed"],
    "nav_riders": ["viz_profile", "viz_rankings", "viz_tyrewhisp"],
    "nav_season": ["viz_championship", "viz_teams", "viz_grid", "viz_reliability"],
    "nav_history": ["viz_circuits", "viz_crossyear"],
}


def remember_selection(widget_key, state_key):
    st.session_state[state_key] = st.session_state[widget_key]


# Keep semantic selections separate from widgets, whose identities change
# when labels are translated or a workspace temporarily hides a control.
st.session_state["nav_group"] = st.session_state.get("selected_nav_group", "nav_overview")
nav_group = st.sidebar.selectbox(
    t("nav_workspace"), list(NAV_GROUPS), format_func=t, key="nav_group",
    on_change=remember_selection, args=("nav_group", "selected_nav_group"),
)
view_keys = NAV_GROUPS[nav_group]
if len(view_keys) == 1:
    view_key = view_keys[0]
else:
    st.session_state[f"view_{nav_group}"] = st.session_state.get(
        f"selected_view_{nav_group}", view_keys[0]
    )
    view_key = st.sidebar.radio(
        t("nav_analysis"), view_keys, format_func=t, key=f"view_{nav_group}",
        on_change=remember_selection, args=(f"view_{nav_group}", f"selected_view_{nav_group}"),
    )
viz = get_translator("en")(view_key)
st.sidebar.divider()


def open_championship(year):
    """Set navigation and filter state before the next Streamlit rerun."""
    st.session_state["selected_nav_group"] = "nav_season"
    st.session_state["selected_view_nav_season"] = "viz_championship"
    st.session_state["sel_year"] = year
    st.session_state.pop("sb_year", None)

# ---------------------------------------------------------------------------
# Sidebar — global filters
# ---------------------------------------------------------------------------

excluded_categories = q(
    f"SELECT DISTINCT category FROM sessions WHERE category IS NULL OR NOT ({PREMIER_CATEGORY})"
)
if not excluded_categories.empty:
    st.sidebar.warning(t("excluded_categories", categories=", ".join(
        excluded_categories["category"].fillna("?").astype(str)
    )))
years_df = premier_q(
    "SELECT DISTINCT season_year FROM events WHERE EXISTS "
    "(SELECT 1 FROM sessions s WHERE s.event_id = events.event_id) ORDER BY season_year DESC"
)
if years_df.empty:
    st.warning(t("no_data_load"))
    st.stop()
year_list = years_df["season_year"].tolist()

needs_session = viz not in ["🏠 Home", "👤 Pilot Profile", "📈 Cross-Year", "🌍 Championship", "🔧 Reliability", "🏢 Teams & Constructors", "🧙 Tyre Whisperers", "🏁 Grid Advantage", "🏟 Circuits", "🏅 Pilot Rankings"]

# Vizs that support "All" aggregation across events/sessions
supports_all = viz in ["⚡ Speed Trap", "🎯 Pilot Rhythm", "⏱ Sector Heatmap"]

# Vizs that only show Race/Sprint in session filter
race_only_session = viz in ["📍 Position Battle", "🛞 Tyre Degradation"]

no_year_filter = viz in ["🏠 Home", "🏟 Circuits", "🏅 Pilot Rankings", "🔧 Reliability", "📈 Cross-Year"]

# Initialize session state for persistent filters
if "sel_year" not in st.session_state:
    st.session_state.sel_year = year_list[0]
if "sel_event_id" not in st.session_state:
    st.session_state.sel_event_id = None
if "sel_session_label" not in st.session_state:
    st.session_state.sel_session_label = None

if not no_year_filter:
    year_options = ["All"] + year_list if supports_all else year_list
    st.session_state["sb_year"] = (
        st.session_state.sel_year if st.session_state.sel_year in year_options else year_options[0]
    )
    selected_year_raw = st.sidebar.selectbox(
        t("season"), year_options, key="sb_year",
        on_change=remember_selection, args=("sb_year", "sel_year"),
    )
    st.session_state.sel_year = selected_year_raw
    all_years = selected_year_raw == "All"
    selected_year = year_list[0] if all_years else selected_year_raw
else:
    selected_year = year_list[0]
    all_years = False

if all_years:
    events_df = premier_q(
        "SELECT event_id, short_name, event_name, sponsored_name, circuit_name, "
        "circuit_place, country_name, date_end, season_year "
        "FROM events WHERE EXISTS (SELECT 1 FROM sessions s WHERE s.event_id = events.event_id) "
        "ORDER BY date_end")
else:
    events_df = premier_q(
        "SELECT event_id, short_name, event_name, sponsored_name, circuit_name, "
        "circuit_place, country_name, date_end, season_year "
        "FROM events WHERE season_year = ? AND EXISTS "
        "(SELECT 1 FROM sessions s WHERE s.event_id = events.event_id) ORDER BY date_end", [selected_year])

sel_session = None
event = None
all_events = False
all_sessions = False

if needs_session:
    if events_df.empty:
        st.info(t("no_events_for_year", year=selected_year)); st.stop()

    evt_labels = [f"{r.short_name} — {r.sponsored_name or r.event_name}" for _, r in events_df.iterrows()]
    event_ids = events_df["event_id"].tolist()
    persisted_event = st.session_state.sel_event_id

    if supports_all and not all_years:
        st.session_state["sb_gp"] = persisted_event if persisted_event in event_ids else None
        gp_sel = st.sidebar.selectbox(
            t("grand_prix"), [None] + event_ids, key="sb_gp",
            format_func=lambda eid: t("all_gp") if eid is None else evt_labels[event_ids.index(eid)],
            on_change=remember_selection, args=("sb_gp", "sel_event_id"),
        )
        all_events = gp_sel is None
        if not all_events:
            event = events_df.iloc[event_ids.index(gp_sel)]
        st.session_state.sel_event_id = event.event_id if event is not None else None
    elif supports_all and all_years:
        all_events = True
    else:
        st.session_state["sb_gp"] = persisted_event if persisted_event in event_ids else event_ids[-1]
        event_id = st.sidebar.selectbox(
            t("grand_prix"), event_ids, key="sb_gp",
            format_func=lambda eid: evt_labels[event_ids.index(eid)],
            on_change=remember_selection, args=("sb_gp", "sel_event_id"),
        )
        event = events_df.iloc[event_ids.index(event_id)]
        st.session_state.sel_event_id = event.event_id

    if not all_events and event is not None:
        sessions_df = premier_q(
            "SELECT session_id, session_type, session_number, session_label, "
            "session_date, weather, air_temp, ground_temp "
            "FROM sessions WHERE event_id = ? ORDER BY session_date",
            [event.event_id])
        if sessions_df.empty:
            st.warning(t("no_sessions")); st.stop()

        if supports_all:
            sess_options = ["All"] + sessions_df["session_label"].tolist()
            st.session_state["sb_sess"] = (
                st.session_state.sel_session_label
                if st.session_state.sel_session_label in sess_options else sess_options[0]
            )
            sel_label = st.sidebar.selectbox(
                t("session"), sess_options, key="sb_sess",
                on_change=remember_selection, args=("sb_sess", "sel_session_label"),
            )
            st.session_state.sel_session_label = sel_label
            all_sessions = sel_label == "All"
            if not all_sessions:
                sel_session = sessions_df[sessions_df["session_label"] == sel_label].iloc[0]
        else:
            if race_only_session:
                avail_sessions = sessions_df[sessions_df["session_type"].isin(["RAC", "SPR"])]
                if avail_sessions.empty:
                    st.warning(t("no_race_sprint_sessions")); st.stop()
            else:
                avail_sessions = sessions_df

            sess_labels = avail_sessions["session_label"].tolist()
            st.session_state["sb_sess"] = (
                st.session_state.sel_session_label
                if st.session_state.sel_session_label in sess_labels else sess_labels[-1]
            )
            sel_label = st.sidebar.selectbox(
                t("session"), sess_labels, key="sb_sess",
                on_change=remember_selection, args=("sb_sess", "sel_session_label"),
            )
            st.session_state.sel_session_label = sel_label
            sel_session = avail_sessions[avail_sessions["session_label"] == sel_label].iloc[0]

        if not all_sessions:
            st.header(f"🏁 {event.sponsored_name or event.event_name}")
            st.caption(
                f"📍 {event.circuit_name}, {event.circuit_place}, {event.country_name} — "
                f"{event.date_end} · {sel_session.weather or ''} · "
                f"{t('air_label')} {sel_session.air_temp or '?'} · {t('track_label')} {sel_session.ground_temp or '?'}")
        else:
            st.header(f"🏁 {event.sponsored_name or event.event_name} — {t('all_sessions_label')}")
    elif all_events:
        scope = t("all_seasons_label") if all_years else str(selected_year)
        st.header(t("all_gp_scope", scope=scope))


# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------

_LAPS_COLS = ("r.full_name AS rider, r.number AS num, "
              "l.lap_number, l.lap_time, l.t1, l.t2, l.t3, l.t4, "
              "l.speed_kmh, l.is_pit, l.run_number, l.front_tyre, l.rear_tyre")

_LAPS_CTX = ("e.season_year AS season, e.short_name AS gp, s.session_label AS session")


@st.cache_data(ttl=300)
def load_laps(sid):
    df = premier_q(f"SELECT {_LAPS_COLS} "
           "FROM laps l JOIN riders r ON l.rider_id = r.rider_id "
           "JOIN sessions s ON l.session_id = s.session_id "
           "WHERE l.session_id = ? ORDER BY r.full_name, l.lap_number", [sid])
    if not df.empty:
        df["lap_sec"] = df["lap_time"].apply(lap_to_sec)
        for c in ["t1", "t2", "t3", "t4"]:
            df[c + "_sec"] = df[c].apply(lap_to_sec)
    return df


@st.cache_data(ttl=300)
def load_laps_multi(event_id=None, year=None):
    """Load laps across multiple sessions with context columns."""
    if event_id:
        df = premier_q(f"SELECT {_LAPS_COLS}, {_LAPS_CTX} "
               "FROM laps l JOIN riders r ON l.rider_id = r.rider_id "
               "JOIN sessions s ON l.session_id = s.session_id "
               "JOIN events e ON s.event_id = e.event_id "
               "WHERE s.event_id = ? "
               "ORDER BY r.full_name, s.session_date, l.lap_number", [event_id])
    elif year and year != "All":
        df = premier_q(f"SELECT {_LAPS_COLS}, {_LAPS_CTX} "
               "FROM laps l JOIN riders r ON l.rider_id = r.rider_id "
               "JOIN sessions s ON l.session_id = s.session_id "
               "JOIN events e ON s.event_id = e.event_id "
               "WHERE e.season_year = ? "
               "ORDER BY r.full_name, e.date_end, s.session_date, l.lap_number", [year])
    else:
        df = premier_q(f"SELECT {_LAPS_COLS}, {_LAPS_CTX} "
               "FROM laps l JOIN riders r ON l.rider_id = r.rider_id "
               "JOIN sessions s ON l.session_id = s.session_id "
               "JOIN events e ON s.event_id = e.event_id "
               "ORDER BY r.full_name, e.date_end, s.session_date, l.lap_number")
    if not df.empty:
        df["lap_sec"] = df["lap_time"].apply(lap_to_sec)
        for c in ["t1", "t2", "t3", "t4"]:
            df[c + "_sec"] = df[c].apply(lap_to_sec)
    return df


@st.cache_data(ttl=300)
def load_class(sid, yr):
    return premier_q("SELECT c.position, r.full_name AS rider, r.number AS num, "
             "t.team_name, t.constructor, c.total_laps, c.time_text, c.gap_first, "
             "c.best_lap_time, c.top_speed, c.points, c.status "
             "FROM classifications c JOIN riders r ON c.rider_id = r.rider_id "
             "JOIN sessions s ON c.session_id = s.session_id "
             "LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = ? "
             "WHERE c.session_id = ? ORDER BY CASE WHEN c.position IS NULL THEN 1 ELSE 0 END, c.position", [yr, sid])


@st.cache_data(ttl=300)
def load_championship(year):
    return premier_q("""
        SELECT e.short_name, e.date_end, r.full_name AS rider,
            SUM(cl.points) AS race_pts
        FROM classifications cl
        JOIN sessions s ON cl.session_id = s.session_id
        JOIN events e ON s.event_id = e.event_id
        JOIN riders r ON cl.rider_id = r.rider_id
        WHERE e.season_year = ? AND s.session_type IN ('RAC', 'SPR')
        GROUP BY e.short_name, e.date_end, r.full_name
        ORDER BY e.date_end
    """, [year])


def championship_points(champ):
    events_order = champ.drop_duplicates("short_name").sort_values("date_end")["short_name"].tolist()
    points = champ.pivot_table(
        index="rider", columns="short_name", values="race_pts", aggfunc="sum", fill_value=0,
    )
    cumulative = points.reindex(columns=events_order).cumsum(axis=1)
    totals = cumulative.iloc[:, -1].sort_values(ascending=False)
    return events_order, cumulative, totals


def clean_laps(df):
    if df.empty:
        return df
    v = df[(df["lap_sec"].notna()) & (df["is_pit"] == False)].copy()
    if v.empty:
        return v
    return v[v["lap_sec"] < v["lap_sec"].median() * 1.15]


def race_elapsed(df):
    """Only contiguous, valid timing from lap one establishes elapsed time."""
    race = df.sort_values(["rider", "lap_number"]).copy()
    if race.empty:
        race["elapsed"] = pd.Series(dtype=float)
        return race
    groups = race.groupby("rider")
    previous = groups["lap_number"].shift().fillna(0)
    valid = (
        race["lap_number"].sub(previous).eq(1)
        & np.isfinite(race["lap_sec"]) & race["lap_sec"].gt(0)
        & ~race.duplicated(["rider", "lap_number"], keep=False)
    )
    complete = valid.groupby(race["rider"]).cummin()
    race["elapsed"] = groups["lap_sec"].cumsum().where(complete)
    return race.drop_duplicates(["rider", "lap_number"])


def reconstructed_positions(laps, classification):
    race = race_elapsed(laps)
    rows = []
    for lap, timing in race.groupby("lap_number"):
        if classification.empty or classification["total_laps"].isna().any():
            continue
        expected = classification.loc[classification["total_laps"] >= lap, "rider"]
        timing = timing[timing["rider"].isin(expected)]
        if expected.empty or set(timing["rider"]) != set(expected) or timing["elapsed"].isna().any():
            continue
        timing = timing[["rider", "lap_number", "elapsed"]].copy()
        timing["pos"] = timing["elapsed"].rank(method="min").astype(int)
        rows.append(timing)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=["rider", "lap_number", "elapsed", "pos"]
    )


if sel_session is not None:
    laps_df = load_laps(sel_session.session_id)
    class_df = load_class(sel_session.session_id, selected_year)
    clean = clean_laps(laps_df)
elif all_events or all_sessions:
    # "All" mode — load laps with context columns
    if all_events:
        laps_df = load_laps_multi(event_id=None, year=None if all_years else selected_year)
    else:  # all_sessions for a single event
        laps_df = load_laps_multi(event_id=event.event_id)
    clean = clean_laps(laps_df)
    class_df = pd.DataFrame()
else:
    laps_df = clean = class_df = pd.DataFrame()

has_context = "gp" in laps_df.columns if not laps_df.empty else False


# =====================================================================
# 🏠 HOME — Championship overview and database coverage
# =====================================================================
if viz == "🏠 Home":
    st.session_state["home_view"] = (
        "home_coverage" if st.session_state.get("selected_home_view") == "home_coverage"
        else "home_championship"
    )
    home_view = st.radio(
        t("home_view"), ["home_championship", "home_coverage"], format_func=t,
        horizontal=True, label_visibility="collapsed", key="home_view",
        on_change=remember_selection, args=("home_view", "selected_home_view"),
    )
    if home_view == "home_championship":
        st.subheader(t("home_championship_title", year=selected_year))
        champ = load_championship(selected_year)
        if champ.empty:
            st.info(t("no_race_sprint_data_for_year", year=selected_year))
            st.caption(t("data_source"))
            st.stop()

        events_order, cumulative, totals = championship_points(champ)
        ranks = totals.rank(ascending=False, method="min").astype(int)
        last_round = champ[champ["short_name"] == events_order[-1]].iloc[0]
        through_date = pd.to_datetime(last_round.date_end).date().isoformat()
        st.caption(t("home_championship_through", gp=events_order[-1], date=through_date))
        for column, (rider, points) in zip(st.columns(3), totals.head(3).items()):
            with column:
                with st.container(border=True):
                    st.caption(f"P{ranks[rider]}")
                    st.subheader(rider)
                    st.metric(t("points"), f"{points:g}")
                    st.caption(t("home_points_behind", points=f"{totals.iloc[0] - points:g}"))

        st.caption(t("home_rounds_imported", count=len(events_order)))
        standings = pd.DataFrame({
            t("position"): ranks,
            t("rider"): totals.index,
            t("points"): totals.values,
            t("home_gap_to_leader"): totals.iloc[0] - totals.values,
        }).reset_index(drop=True)
        table_column, chart_column = st.columns([1, 1.5])
        with table_column:
            st.subheader(t("current_standings"))
            st.dataframe(
                standings, width="stretch", hide_index=True,
                height=min(550, 38 + 35 * len(standings)),
            )
        with chart_column:
            st.subheader(t("home_title_race"))
            top_riders = totals.head(5).index
            progress = cumulative.loc[top_riders].T.rename_axis("event").reset_index()
            progress = progress.melt(id_vars="event", var_name="rider", value_name="points")
            fig = px.line(
                progress, x="event", y="points", color="rider", markers=True,
                labels={"event": t("grand_prix_label"), "points": t("points"), "rider": t("rider")},
                category_orders={"event": events_order},
            )
            fig.update_layout(height=420, hovermode="x unified")
            st.plotly_chart(fig, width="stretch")
        st.caption(t("home_championship_method"))
        st.button(
            t("home_explore_championship"), type="primary", width="stretch",
            on_click=open_championship, args=(selected_year,),
        )
        st.divider()
        st.caption(t("home_loaded_note"))
        st.caption(t("data_source"))
        st.stop()

    st.header(t("home_title"))

    stats = premier_q("""
        SELECT
            (SELECT COUNT(*) FROM events e WHERE EXISTS
                (SELECT 1 FROM sessions s WHERE s.event_id = e.event_id)) AS n_events,
            (SELECT COUNT(*) FROM sessions) AS n_sessions,
            (SELECT COUNT(*) FROM classifications c JOIN sessions s ON c.session_id = s.session_id) AS n_classifications,
            (SELECT COUNT(*) FROM laps l JOIN sessions s ON l.session_id = s.session_id) AS n_laps,
            (SELECT COUNT(DISTINCT rider_id) FROM (
                SELECT c.rider_id FROM classifications c JOIN sessions s ON c.session_id = s.session_id
                UNION SELECT l.rider_id FROM laps l JOIN sessions s ON l.session_id = s.session_id
            ) participants) AS n_riders,
            (SELECT COUNT(*) FROM teams t WHERE EXISTS (
                SELECT 1 FROM classifications c JOIN sessions s ON c.session_id = s.session_id
                JOIN events e ON s.event_id = e.event_id
                WHERE c.team_id = t.team_id AND e.season_year = t.season_year)) AS n_teams,
            (SELECT COUNT(DISTINCT season_year) FROM events e WHERE EXISTS
                (SELECT 1 FROM sessions s WHERE s.event_id = e.event_id)) AS n_seasons,
            (SELECT MIN(season_year) FROM events e WHERE EXISTS
                (SELECT 1 FROM sessions s WHERE s.event_id = e.event_id)) AS min_year,
            (SELECT MAX(season_year) FROM events e WHERE EXISTS
                (SELECT 1 FROM sessions s WHERE s.event_id = e.event_id)) AS max_year,
            (SELECT COUNT(DISTINCT circuit_name) FROM events e WHERE EXISTS
                (SELECT 1 FROM sessions s WHERE s.event_id = e.event_id)) AS n_circuits,
            (SELECT COUNT(DISTINCT country_name) FROM events e WHERE EXISTS
                (SELECT 1 FROM sessions s WHERE s.event_id = e.event_id)) AS n_countries
    """)
    s = stats.iloc[0]

    st.subheader(t("home_seasons_subheader", min_year=int(s.min_year), max_year=int(s.max_year)))

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(t("metric_seasons"), int(s.n_seasons))
    c2.metric(t("home_gp_count"), int(s.n_events))
    c3.metric(t("home_sessions_count"), int(s.n_sessions))
    c4.metric(t("home_riders_count"), int(s.n_riders))
    c5.metric(t("home_laps_count"), f"{int(s.n_laps):,}")
    c6.metric(t("home_circuits_count"), int(s.n_circuits))

    st.divider()

    # Events per season
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader(t("races_per_season"))
        evts_yr = premier_q(
            "SELECT season_year AS Year, COUNT(*) AS Events FROM events WHERE EXISTS "
            "(SELECT 1 FROM sessions s WHERE s.event_id = events.event_id) "
            "GROUP BY season_year ORDER BY season_year"
        )
        evts_yr["Year"] = evts_yr["Year"].astype(str)
        fig = px.bar(evts_yr, x="Year", y="Events", text="Events",
                     color="Events", color_continuous_scale="Blues")
        fig.update_layout(height=350, coloraxis_showscale=False,
                          yaxis=dict(range=[0, evts_yr["Events"].max() * 1.2]))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, width="stretch")

    with col_right:
        st.subheader(t("laps_per_season"))
        data_cov = premier_q("""
            SELECT e.season_year AS Year, COUNT(*) AS Laps,
                SUM(CASE WHEN l.t1 IS NOT NULL THEN 1 ELSE 0 END) AS With_Sectors
            FROM laps l JOIN sessions s ON l.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            GROUP BY e.season_year ORDER BY e.season_year
        """)
        data_cov["Year"] = data_cov["Year"].astype(str)
        data_cov["No Sectors"] = data_cov["Laps"] - data_cov["With_Sectors"]
        fig = px.bar(data_cov, x="Year",
                     y=["With_Sectors", "No Sectors"],
                     title=t("laps_sector_per_season"),
                     labels={"value": t("lap_entries"), "variable": ""},
                     color_discrete_map={"With_Sectors": "#2ecc71", "No Sectors": "#e0e0e0"},
                     barmode="stack")
        fig.update_layout(height=350,
                          yaxis=dict(range=[0, data_cov["Laps"].max() * 1.2]),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        # Add text labels for total laps
        fig.add_trace(go.Scatter(
            x=data_cov["Year"], y=data_cov["Laps"],
            mode="text", text=data_cov["Laps"].astype(str),
            textposition="top center", textfont=dict(size=10),
            showlegend=False,
        ))
        st.plotly_chart(fig, width="stretch")

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader(t("top_riders_wins"))
        wins = premier_q("""
            SELECT TOP 10 r.full_name AS Rider, COUNT(*) AS Wins
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE s.session_type = 'RAC' AND c.position = 1
            GROUP BY r.full_name ORDER BY Wins DESC
        """)
        if not wins.empty:
            fig = px.bar(wins, x="Rider", y="Wins", text="Wins",
                         color="Wins", color_continuous_scale="YlOrRd")
            fig.update_layout(height=350, coloraxis_showscale=False, xaxis_tickangle=-45,
                              yaxis=dict(range=[0, wins["Wins"].max() * 1.2]))
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, width="stretch")

    with col_b:
        st.subheader(t("constructors_wins"))
        const_wins = premier_q("""
            SELECT t.constructor AS Constructor, COUNT(*) AS Wins
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
            WHERE s.session_type = 'RAC' AND c.position = 1 AND t.constructor IS NOT NULL
            GROUP BY t.constructor ORDER BY Wins DESC
        """)
        if not const_wins.empty:
            fig = px.pie(const_wins, values="Wins", names="Constructor",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=350)
            st.plotly_chart(fig, width="stretch")

    st.divider()

    col_x, col_y = st.columns(2)

    with col_x:
        st.subheader(t("countries_visited"))
        countries = premier_q("""
            SELECT country_name AS Country, COUNT(*) AS Races
            FROM events WHERE EXISTS (SELECT 1 FROM sessions s WHERE s.event_id = events.event_id)
            GROUP BY country_name ORDER BY Races DESC
        """)
        st.dataframe(countries, width="stretch", hide_index=True, height=300)

    with col_y:
        st.subheader(t("sessions_by_type"))
        sess_types = premier_q("""
            SELECT session_type AS Type,
                CASE session_type
                    WHEN 'FP' THEN 'Free Practice'
                    WHEN 'P' THEN 'Practice'
                    WHEN 'PR' THEN 'Practice'
                    WHEN 'Q' THEN 'Qualifying'
                    WHEN 'SPR' THEN 'Sprint Race'
                    WHEN 'WUP' THEN 'Warm Up'
                    WHEN 'RAC' THEN 'Race'
                    ELSE session_type
                END AS Label,
                COUNT(*) AS Count
            FROM sessions GROUP BY session_type ORDER BY Count DESC
        """)
        fig = px.bar(sess_types, x="Label", y="Count", text="Count",
                     color="Label", color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(height=300, showlegend=False,
                          yaxis=dict(range=[0, sess_types["Count"].max() * 1.2]))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, width="stretch")
        st.markdown(t("session_types_explainer"))

    st.divider()

    # --- Data Quality ---
    st.subheader(t("data_quality_title"))
    st.caption(t("data_quality_caption"))

    dq = premier_q("""
        SELECT e.season_year AS Year,
            COUNT(DISTINCT e.event_id) AS Events,
            COUNT(DISTINCT s.session_id) AS Sessions,
            (SELECT COUNT(*) FROM classifications c2 
             JOIN sessions s2 ON c2.session_id = s2.session_id
             JOIN events e2 ON s2.event_id = e2.event_id
             WHERE e2.season_year = e.season_year) AS Classifications,
            (SELECT COUNT(*) FROM laps l2 
             JOIN sessions s2 ON l2.session_id = s2.session_id
             JOIN events e2 ON s2.event_id = e2.event_id
             WHERE e2.season_year = e.season_year) AS Laps,
            (SELECT COUNT(*) FROM laps l3
             JOIN sessions s3 ON l3.session_id = s3.session_id
             JOIN events e3 ON s3.event_id = e3.event_id
             WHERE e3.season_year = e.season_year AND l3.t1 IS NOT NULL) AS Sectors
        FROM events e
        JOIN sessions s ON s.event_id = e.event_id
        GROUP BY e.season_year ORDER BY e.season_year
    """)
    if not dq.empty:
        dq["Year"] = dq["Year"].astype(str)
        dq["Lap Coverage %"] = (dq["Laps"] / dq["Laps"].max() * 100).fillna(0).round(0).astype(int)
        dq["Sector Coverage %"] = np.where(dq["Laps"] > 0,
            (dq["Sectors"] / dq["Laps"] * 100).fillna(0).round(0), 0).astype(int)
        dq["Has PDF Data"] = dq["Laps"].apply(lambda x: "✅" if x > 1000 else ("⚠️" if x > 0 else "❌"))

        fig = go.Figure()
        fig.add_trace(go.Bar(x=dq["Year"], y=dq["Classifications"], name=t("classifications"),
                             marker_color="#3498db"))
        fig.add_trace(go.Bar(x=dq["Year"], y=dq["Laps"], name=t("lap_entries"),
                             marker_color="#2ecc71"))
        fig.add_trace(go.Bar(x=dq["Year"], y=dq["Sectors"], name=t("sector_entries"),
                             marker_color="#f39c12"))
        fig.update_layout(height=400, barmode="group",
                          title=t("data_coverage_by_year"),
                          yaxis_title=t("records"),
                          hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

        # Summary table
        display = dq[["Year", "Events", "Sessions", "Classifications", "Laps", "Sectors",
                       "Sector Coverage %", "Has PDF Data"]].copy()
        st.dataframe(display, width="stretch", hide_index=True)

    st.divider()
    st.caption(t("data_source")) #.pulselive.com + resources.motogp.com (official timing PDFs)")


# =====================================================================
# 🎯 PILOT RHYTHM
# =====================================================================
elif viz == "🎯 Pilot Rhythm":
    st.subheader(t("rhythm_title"))
    st.caption(t("rhythm_caption"))
    if clean.empty:
        st.info(t("no_lap_data")); st.stop()

    n = st.slider(t("best_n_laps"), 1, 20, 5)
    riders_sorted = clean.groupby("rider")["lap_sec"].min().sort_values().index.tolist()
    data = {}
    for rider in riders_sorted:
        data[rider] = list(clean[clean["rider"] == rider]["lap_sec"].nsmallest(n).values)
    maxlen = max(len(v) for v in data.values())
    for r in data:
        data[r] += [np.nan] * (maxlen - len(data[r]))

    tdf = pd.DataFrame(data, index=[f"Lap {i+1}" for i in range(maxlen)])
    avg = tdf.mean()
    tdf.loc["AVERAGE"] = avg
    tdf = tdf[avg.sort_values().index]

    vals = tdf.values.flatten()
    vals = vals[~np.isnan(vals)]
    vmin, vmax = vals.min(), vals.max()

    styled = (tdf.style.format(fmt)
              .map(lambda v: green_red_style(v, vmin, vmax))
              .apply(lambda row: ["font-weight:bold; border-top:2px solid #333"] * len(row)
                     if row.name == "AVERAGE" else [""] * len(row), axis=1))
    st.dataframe(styled, width="stretch", height=min(650, (maxlen + 2) * 40))

    ac = avg.sort_values().reset_index()
    ac.columns = ["Rider", "Avg"]
    ac["Delta"] = ac["Avg"] - ac["Avg"].min()
    ac["Label"] = ac["Avg"].apply(fmt)
    fig = px.bar(ac, x="Rider", y="Delta", text="Label",
                 title=t("avg_best_laps", n=n),
                 color="Delta", color_continuous_scale="RdYlGn_r")
    fig.update_layout(height=420, xaxis_tickangle=-45, coloraxis_showscale=False)
    fig.update_traces(textposition="outside", textfont_size=10)
    st.plotly_chart(fig, width="stretch")


# =====================================================================
# 🏎 LAP TIMES
# =====================================================================
elif viz == "🏎 Lap Times":
    st.subheader(t("laptimes_title"))
    if clean.empty:
        st.info(t("no_lap_data")); st.stop()
    all_r = sorted(clean["rider"].unique())
    default = [r for r in class_df["rider"].tolist() if r in all_r][:5] if not class_df.empty else all_r[:5]
    sel = st.multiselect(t("riders"), all_r, default=[r for r in default if r in all_r])
    if sel:
        f = clean[clean["rider"].isin(sel)]
        fig = px.line(f, x="lap_number", y="lap_sec", color="rider", markers=True,
                      title=t("lap_time_per_lap"),
                      labels={"lap_number": t("lap"), "lap_sec": t("time_s")})
        fig.update_layout(height=500, hovermode="x unified")
        st.plotly_chart(fig, width="stretch")
        if len(sel) > 1 and sel_session.session_type in ("RAC", "SPR"):
            timing = race_elapsed(laps_df[laps_df["rider"].isin(sel)])
            cum = timing.pivot(index="lap_number", columns="rider", values="elapsed")
            cum = cum.where(cum.notna().all(axis=1), axis=0)
            gap = cum.sub(cum.min(axis=1), axis=0).reset_index().melt(
                id_vars="lap_number", var_name="rider", value_name="gap")
            st.caption(t("race_timing_limits"))
            fig2 = px.line(gap, x="lap_number", y="gap", color="rider",
                           title=t("cumulative_gap"),
                           labels={"lap_number": t("lap"), "gap": t("gap") + " (s)"})
            fig2.update_layout(height=400)
            fig2.update_traces(connectgaps=False)
            st.plotly_chart(fig2, width="stretch")
        elif len(sel) > 1:
            st.info(t("race_timing_only"))


# =====================================================================
# 📍 POSITION BATTLE
# =====================================================================
elif viz == "📍 Position Battle":
    st.subheader(t("position_title"))
    st.caption(t("position_caption"))

    if laps_df.empty or laps_df["lap_sec"].isna().all():
        st.info(t("no_lap_data")); st.stop()

    pos_df = reconstructed_positions(laps_df, class_df)
    if pos_df.empty:
        st.info(t("no_position_data")); st.stop()
    st.caption(t("race_timing_limits"))
    last_lap = int(laps_df["lap_number"].max())
    pos_df = pos_df.set_index(["rider", "lap_number"]).reindex(
        pd.MultiIndex.from_product(
            [pos_df["rider"].unique(), range(1, last_lap + 1)], names=["rider", "lap_number"]
        )
    ).reset_index()

    all_r = sorted(pos_df["rider"].unique())
    if not class_df.empty:
        top5 = [r for r in class_df["rider"].tolist() if r in all_r][:5]
    else:
        top5 = all_r[:5]
    sel = st.multiselect(t("riders"), all_r, default=top5, key="pos_r")
    if sel:
        fig = px.line(pos_df[pos_df["rider"].isin(sel)], x="lap_number", y="pos",
                      color="rider", markers=True, title=t("position_per_lap"),
                      labels={"lap_number": t("lap"), "pos": t("position")})
        max_pos_val = int(pos_df[pos_df["rider"].isin(sel)]["pos"].max())
        fig.update_traces(connectgaps=False)
        fig.update_layout(height=500,
                          yaxis=dict(autorange=False, dtick=1, range=[max_pos_val + 0.5, 0.5], tick0=1),
                          xaxis=dict(dtick=1, tick0=0),
                          hovermode="x unified")
        st.plotly_chart(fig, width="stretch")


# =====================================================================
# 📊 LAP DISTRIBUTION — violin/box plots for consistency analysis
# =====================================================================
elif viz == "📊 Lap Distribution":
    st.subheader(t("distribution_title"))
    st.caption(t("distribution_caption"))
    if clean.empty:
        st.info(t("no_lap_data")); st.stop()

    all_r = sorted(clean["rider"].unique())
    default = [r for r in class_df["rider"].tolist() if r in all_r][:8] if not class_df.empty else all_r[:8]
    sel = st.multiselect(t("riders"), all_r, default=default, key="dist_r")

    if not sel:
        st.info(t("select_rider")); st.stop()

    f = clean[clean["rider"].isin(sel)].copy()

    # Sort riders by median lap time (fastest first)
    rider_order = f.groupby("rider")["lap_sec"].median().sort_values().index.tolist()

    chart_type = st.radio(t("chart_type"), [t("chart_violin"), t("chart_box_strip"), t("chart_ridge")], horizontal=True)

    if chart_type == t("chart_violin"):
        st.markdown(t("violin_explanation"))
        fig = px.violin(f, x="rider", y="lap_sec", color="rider", box=True, points="all",
                        title=t("violin_plot_title"),
                        labels={"lap_sec": t("lap_time_s"), "rider": ""},
                        category_orders={"rider": rider_order})
        fig.update_traces(meanline_visible=True, pointpos=-0.5, jitter=0.3, marker_size=4)
        fig.update_layout(height=550, showlegend=False)
        st.plotly_chart(fig, width="stretch")

    elif chart_type == t("chart_box_strip"):
        st.markdown(t("box_explanation"))
        fig = px.box(f, x="rider", y="lap_sec", color="rider", points="all",
                     title=t("box_strip_title"),
                     labels={"lap_sec": t("lap_time_s"), "rider": ""},
                     category_orders={"rider": rider_order})
        fig.update_traces(jitter=0.4, marker_size=4)
        fig.update_layout(height=550, showlegend=False)
        st.plotly_chart(fig, width="stretch")

    else:  # Ridge / Histogram
        st.markdown(t("ridge_explanation"))
        fig = go.Figure()
        for rider in reversed(rider_order):
            rd = f[f["rider"] == rider]["lap_sec"].dropna()
            fig.add_trace(go.Violin(
                x=rd, name=rider, side="positive",
                meanline_visible=True, line_color=None,
            ))
        fig.update_traces(orientation="h", width=1.8, points=False)
        fig.update_layout(
            title=t("ridge_plot_title"),
            height=max(400, len(rider_order) * 60),
            xaxis_title=t("lap_time_s"),
            showlegend=False,
            violinmode="overlay",
        )
        st.plotly_chart(fig, width="stretch")

    # Stats table
    st.subheader(t("consistency_stats"))
    st.markdown(t("consistency_explanation"))
    stats = f.groupby("rider").agg(
        Median=("lap_sec", "median"),
        Mean=("lap_sec", "mean"),
        Std=("lap_sec", "std"),
        Min=("lap_sec", "min"),
        Max=("lap_sec", "max"),
        Laps=("lap_sec", "count"),
    ).reset_index()
    stats = stats.sort_values("Median")
    stats["Range"] = (stats["Max"] - stats["Min"]).round(3)
    stats["Std"] = stats["Std"].round(3)
    for c in ["Median", "Mean", "Min", "Max"]:
        stats[c] = stats[c].apply(fmt)
    stats.columns = ["Rider", "Median", "Mean", "Std Dev", "Fastest", "Slowest", "Laps", "Range (s)"]
    st.dataframe(stats, width="stretch", hide_index=True)

    # Sector-level beeswarm
    st.subheader(t("sector_clustering"))
    st.markdown(t("sector_clustering_explanation"))
    sector = st.selectbox(t("sector_label"), ["T1", "T2", "T3", "T4"], key="dist_sector")
    sec_col = sector.lower() + "_sec"
    f_sec = f[f[sec_col].notna()].copy()
    if not f_sec.empty:
        fig2 = px.strip(f_sec, x="rider", y=sec_col, color="rider",
                        title=t("sector_time_distribution", num=sector[-1]),
                        labels={sec_col: t("sector_time_s", sector=sector), "rider": ""},
                        category_orders={"rider": rider_order})
        fig2.update_traces(jitter=0.6, marker_size=5, marker_opacity=0.6)
        fig2.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig2, width="stretch")


# =====================================================================
# ⏱ SECTOR HEATMAP
# =====================================================================
elif viz == "⏱ Sector Heatmap":
    st.subheader(t("sector_analysis_title"))
    if clean.empty:
        st.info(t("no_data")); st.stop()
    sb = clean.groupby("rider").agg(T1=("t1_sec", "min"), T2=("t2_sec", "min"),
                                     T3=("t3_sec", "min"), T4=("t4_sec", "min"),
                                     Best=("lap_sec", "min")).reset_index()
    sb["Ideal"] = sb[["T1", "T2", "T3", "T4"]].sum(axis=1, min_count=4)
    if sb["Ideal"].isna().any():
        st.info(t("incomplete_sectors"))
    sb = sb.sort_values("Best")
    for c in ["T1", "T2", "T3", "T4"]:
        sb[c + "_d"] = sb[c] - sb[c].min()
    fig = go.Figure(data=go.Heatmap(
        z=sb[["T1_d", "T2_d", "T3_d", "T4_d"]].values,
        x=["T1", "T2", "T3", "T4"], y=sb["rider"].values,
        colorscale="RdYlGn_r",
        text=sb[["T1", "T2", "T3", "T4"]].round(3).values, texttemplate="%{text}",
        hovertemplate="Rider: %{y}<br>Sector: %{x}<br>Delta: +%{z:.3f}s<extra></extra>"))
    fig.update_layout(title=t("best_sector_times_delta"),
                      height=max(400, len(sb) * 28), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch")
    st.subheader(t("ideal_vs_actual"))
    cmp = sb[["rider", "Best", "Ideal"]].copy()
    cmp["Gap"] = (cmp["Best"] - cmp["Ideal"]).round(3)
    cmp["Best"] = cmp["Best"].apply(fmt)
    cmp["Ideal"] = cmp["Ideal"].apply(fmt)
    st.dataframe(cmp.head(22), width="stretch", hide_index=True)


# =====================================================================
# 🛞 TYRE DEGRADATION
# =====================================================================
elif viz == "🛞 Tyre Degradation":
    st.subheader(t("tyre_degradation_title"))
    if clean.empty:
        st.info(t("no_data")); st.stop()
    v = clean[clean["lap_number"] > 1].copy()
    all_r = sorted(v["rider"].unique())
    default = [r for r in class_df["rider"].tolist() if r in all_r][:5] if not class_df.empty else all_r[:3]
    sel = st.multiselect(t("riders"), all_r, default=[r for r in default if r in all_r], key="tyre_r")
    if sel:
        f = v[v["rider"].isin(sel)].copy()
        f["stint_lap"] = f.groupby(["rider", "run_number"]).cumcount() + 1
        f["label"] = f["rider"] + " (" + f["rear_tyre"].fillna("?") + ")"
        fig = px.scatter(f, x="stint_lap", y="lap_sec", color="label", trendline="lowess",
                         title=t("lap_time_vs_tyre"),
                         labels={"stint_lap": t("laps_on_tyre"), "lap_sec": t("time_s")})
        fig.update_layout(height=500)
        st.plotly_chart(fig, width="stretch")


# =====================================================================
# 🧙 TYRE WHISPERERS
# =====================================================================
elif viz == "🧙 Tyre Whisperers":
    st.header(t("tyre_whisperer_header", year=selected_year))
    st.caption(t("tyre_whisperer_caption"))

    # Load all race laps for the season
    race_laps = premier_q("""
        SELECT e.short_name AS gp, e.date_end, s.session_id,
            r.full_name AS rider, l.lap_number, l.lap_time, l.speed_kmh
        FROM laps l
        JOIN riders r ON l.rider_id = r.rider_id
        JOIN sessions s ON l.session_id = s.session_id
        JOIN events e ON s.event_id = e.event_id
        WHERE e.season_year = ? AND s.session_type = 'RAC'
            AND l.is_pit = 0
        ORDER BY e.date_end, r.full_name, l.lap_number
    """, [selected_year])

    if race_laps.empty:
        st.info(t("no_race_lap_data")); st.stop()

    race_laps["lap_sec"] = race_laps["lap_time"].apply(lap_to_sec)
    race_laps = race_laps.dropna(subset=["lap_sec"])
    # Remove outliers (slow laps from incidents)
    med = race_laps.groupby(["gp", "rider"])["lap_sec"].transform("median")
    race_laps = race_laps[race_laps["lap_sec"] < med * 1.10]

    all_scores = []
    gp_list = race_laps.drop_duplicates("gp").sort_values("date_end")["gp"].tolist()

    for gp in gp_list:
        gp_data = race_laps[race_laps["gp"] == gp]
        riders_in_gp = gp_data["rider"].unique()

        for rider in riders_in_gp:
            rlaps = gp_data[gp_data["rider"] == rider].sort_values("lap_number")
            n = len(rlaps)
            if n < 6:
                continue
            third = n // 3
            first_avg = rlaps.head(third)["lap_sec"].mean()
            last_avg = rlaps.tail(third)["lap_sec"].mean()
            degradation = last_avg - first_avg  # positive = got slower

            all_scores.append({
                "gp": gp,
                "rider": rider,
                "first_third_avg": round(first_avg, 3),
                "last_third_avg": round(last_avg, 3),
                "degradation": round(degradation, 3),
                "laps": n,
            })

    if not all_scores:
        st.info(t("not_enough_data")); st.stop()

    scores_df = pd.DataFrame(all_scores)

    # Compute field average degradation per GP, then rider's advantage
    gp_avg_deg = scores_df.groupby("gp")["degradation"].mean().rename("field_avg_deg")
    scores_df = scores_df.merge(gp_avg_deg, on="gp")
    scores_df["advantage"] = scores_df["field_avg_deg"] - scores_df["degradation"]
    # Positive advantage = less degradation than field = better tyre management

    # Season-level Tyre Whisperer score: average advantage across races
    season_score = scores_df.groupby("rider").agg(
        avg_advantage=("advantage", "mean"),
        avg_degradation=("degradation", "mean"),
        races=("gp", "nunique"),
    ).reset_index()
    season_score = season_score[season_score["races"] >= 3]
    season_score = season_score.sort_values("avg_advantage", ascending=False)
    season_score["avg_advantage"] = season_score["avg_advantage"].round(3)
    season_score["avg_degradation"] = season_score["avg_degradation"].round(3)

    # Bar chart: Tyre Whisperer ranking
    st.subheader(t("tyre_whisperer_ranking"))
    fig = px.bar(
        season_score, x="rider", y="avg_advantage",
        color="avg_advantage",
        color_continuous_scale=["#e74c3c", "#f39c12", "#2ecc71"],
        title=t("tyre_whisperer_score_title", year=selected_year),
        labels={"rider": "", "avg_advantage": t("advantage_s_lap")},
        text=season_score["avg_advantage"].apply(lambda x: f"+{x:.3f}" if x > 0 else f"{x:.3f}"),
    )
    fig.update_layout(height=500, xaxis_tickangle=-45, coloraxis_showscale=False)
    fig.update_traces(textposition="outside", textfont_size=10)
    st.plotly_chart(fig, width="stretch")

    # Heatmap: per-GP advantage
    st.subheader(t("per_race_tyre_advantage"))
    st.caption(t("tyre_advantage_caption"))
    heat_data = scores_df.pivot_table(index="rider", columns="gp", values="advantage", aggfunc="first")
    # Order columns by calendar, rows by season score
    heat_data = heat_data[[g for g in gp_list if g in heat_data.columns]]
    top_riders = season_score["rider"].tolist()
    heat_data = heat_data.reindex([r for r in top_riders if r in heat_data.index])

    fig2 = go.Figure(data=go.Heatmap(
        z=heat_data.values,
        x=heat_data.columns.tolist(),
        y=heat_data.index.tolist(),
        colorscale=[[0, "#e74c3c"], [0.5, "#ffffcc"], [1.0, "#2ecc71"]],
        zmid=0,
        text=heat_data.round(2).values,
        texttemplate="%{text}",
        hovertemplate="Rider: %{y}<br>GP: %{x}<br>Advantage: %{z:.3f} s/lap<extra></extra>",
    ))
    fig2.update_layout(
        height=max(450, len(heat_data) * 28),
        yaxis=dict(autorange="reversed"),
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig2, width="stretch")

    # Detailed table
    st.subheader(t("detailed_scores"))
    display_score = season_score.copy()
    display_score.columns = [t("rider"), t("tyre_advantage_col"), t("avg_degradation_col"), t("races")]
    st.dataframe(display_score, width="stretch", hide_index=True)

    with st.expander(t("how_calculated")):
        st.markdown(t("tyre_calculation_explanation"))


# =====================================================================
# ⚡ SPEED TRAP
# =====================================================================
elif viz == "⚡ Speed Trap":
    st.subheader(t("speed_trap_title"))
    if laps_df.empty:
        st.info(t("no_data")); st.stop()
    v = laps_df[laps_df["speed_kmh"].notna() & (laps_df["speed_kmh"] > 0)].copy()
    if v.empty:
        st.info(t("no_speed_data")); st.stop()

    all_r = sorted(v["rider"].unique())
    default = [r for r in class_df["rider"].tolist() if r in all_r][:8] if not class_df.empty else all_r[:8]
    sel = st.multiselect(t("riders_leave_empty"), all_r,
                         default=[r for r in default if r in all_r], key="spd_r")

    vf = v[v["rider"].isin(sel)] if sel else v

    # Max speed per rider bar chart
    if has_context:
        idx = vf.groupby("rider")["speed_kmh"].idxmax()
        ms = vf.loc[idx, ["rider", "speed_kmh", "season", "gp", "session"]].sort_values("speed_kmh", ascending=False)
        ms.columns = ["Rider", "Top Speed (km/h)", "Season", "GP", "Session"]
        fig = px.bar(ms.head(22), x="Rider", y="Top Speed (km/h)",
                     hover_data={"Season": True, "GP": True, "Session": True},
                     title=t("max_speed_per_rider"), color="Top Speed (km/h)",
                     color_continuous_scale="Turbo")
    else:
        ms = vf.groupby("rider")["speed_kmh"].max().sort_values(ascending=False).reset_index()
        ms.columns = ["Rider", "Top Speed (km/h)"]
        fig = px.bar(ms.head(22), x="Rider", y="Top Speed (km/h)",
                     title=t("max_speed_per_rider"), color="Top Speed (km/h)",
                     color_continuous_scale="Turbo")

    smin, smax = ms["Top Speed (km/h)"].min(), ms["Top Speed (km/h)"].max()
    margin = max(2, (smax - smin) * 0.15)
    fig.update_layout(height=450, xaxis_tickangle=-45, coloraxis_showscale=False,
                      yaxis=dict(range=[smin - margin, smax + margin]))
    st.plotly_chart(fig, width="stretch")

    if sel:
        f = vf
        fmin, fmax = f["speed_kmh"].min(), f["speed_kmh"].max()
        fmargin = max(2, (fmax - fmin) * 0.15)
        spd_floor, spd_ceil = fmin - fmargin, fmax + fmargin

        if has_context:
            fig2 = px.box(f, x="rider", y="speed_kmh", color="rider",
                          hover_data=["season", "gp", "session"],
                          title=t("speed_distribution"), labels={"speed_kmh": t("kmh"), "rider": ""})
        else:
            fig2 = px.box(f, x="rider", y="speed_kmh", color="rider",
                          title=t("speed_distribution"), labels={"speed_kmh": t("kmh"), "rider": ""})
        fig2.update_layout(height=400, showlegend=False, yaxis=dict(range=[spd_floor, spd_ceil]))
        st.plotly_chart(fig2, width="stretch")

        if has_context:
            gp_order = events_df.sort_values("date_end")["short_name"].unique().tolist()
            fig3 = px.scatter(f, x="gp", y="speed_kmh", color="rider",
                              hover_data=["season", "session", "lap_number"],
                              title=t("speed_across_gp"),
                              labels={"gp": t("grand_prix_label"), "speed_kmh": t("kmh")},
                              category_orders={"gp": gp_order})
            fig3.update_layout(height=400, xaxis_tickangle=-45, yaxis=dict(range=[spd_floor, spd_ceil]))
        else:
            fig3 = px.line(f, x="lap_number", y="speed_kmh", color="rider", markers=True,
                           title=t("speed_per_lap"), labels={"lap_number": t("lap"), "speed_kmh": t("kmh")})
            fig3.update_layout(height=400, hovermode="x unified", yaxis=dict(range=[spd_floor, spd_ceil]))
        st.plotly_chart(fig3, width="stretch")


# =====================================================================
# 🏆 CLASSIFICATION
# =====================================================================
elif viz == "🏆 Classification":
    st.subheader(t("classification_header", session=sel_session.session_label))
    if class_df.empty:
        st.info(t("no_data")); st.stop()
    display = class_df.copy()
    display["position"] = display["position"].apply(lambda x: int(x) if pd.notna(x) else "")
    display["points"] = display["points"].apply(lambda x: int(x) if pd.notna(x) else "")

    # For race/sprint sessions, the API doesn't return best_lap/top_speed — fill from laps table
    if not clean.empty and display["best_lap_time"].isna().all():
        best_per_rider = clean.groupby("rider").agg(
            best_lap_time=("lap_time", lambda x: x.loc[clean.loc[x.index, "lap_sec"].idxmin()] if not x.empty else None),
            top_speed=("speed_kmh", "max"),
        ).reset_index()
        display = display.drop(columns=["best_lap_time", "top_speed"]).merge(
            best_per_rider, on="rider", how="left")

    display["top_speed"] = display["top_speed"].apply(lambda x: x if pd.notna(x) else "")

    def hl(row):
        fills = {1: "#FFF4CC", 2: "#E8E8E8", 3: "#F5DEB3"}
        bg = fills.get(row.position, "")
        if bg:
            return [f"background-color: {bg}; color: #1a1a1a; font-weight: bold"] * len(row)
        return [""] * len(row)
    st.dataframe(display.style.apply(hl, axis=1), width="stretch", hide_index=True, height=650)


# =====================================================================
# 🌍 CHAMPIONSHIP STANDINGS
# =====================================================================
elif viz == "🌍 Championship":
    st.header(t("championship_header", year=selected_year))
    st.caption(t("championship_caption"))

    champ = load_championship(selected_year)

    if champ.empty:
        st.info(t("no_race_sprint_data_for_year", year=selected_year)); st.stop()

    events_order, cum, final_pts = championship_points(champ)

    # Rank at each event (1 = leader)
    ranks = cum.rank(ascending=False, method="min").astype(int)

    # Focus on top N riders (by final standings)
    n_riders = st.slider(t("show_top_n"), 5, 22, 10)
    top_riders = final_pts.head(n_riders).index.tolist()

    # --- Chart 1: Championship position evolution ---
    st.subheader(t("championship_position_per_race"))
    ranks_top = ranks.loc[top_riders]
    ranks_plot = ranks_top.T.rename_axis("event").reset_index()
    ranks_melt = ranks_plot.melt(id_vars="event", var_name="rider", value_name="position")

    max_pos = int(ranks_melt["position"].max())
    fig = px.line(ranks_melt, x="event", y="position", color="rider", markers=True,
                  title=t("championship_pos_title", year=selected_year),
                  labels={"event": t("grand_prix_label"), "position": t("championship_position_label")},
                  category_orders={"event": events_order})
    fig.update_layout(height=550, yaxis=dict(autorange=False, dtick=1, range=[max_pos + 0.5, 0.5], tick0=1),
                      hovermode="x unified", xaxis_tickangle=-45)
    st.plotly_chart(fig, width="stretch")

    # --- Chart 2: Cumulative points ---
    st.subheader(t("cumulative_points"))
    cum_top = cum.loc[top_riders]
    cum_plot = cum_top.T.rename_axis("event").reset_index()
    cum_melt = cum_plot.melt(id_vars="event", var_name="rider", value_name="points")

    fig2 = px.line(cum_melt, x="event", y="points", color="rider", markers=True,
                   title=t("championship_pts_title", year=selected_year),
                   labels={"event": t("grand_prix_label"), "points": t("points")},
                   category_orders={"event": events_order})
    fig2.update_layout(height=500, hovermode="x unified", xaxis_tickangle=-45)
    st.plotly_chart(fig2, width="stretch")

    # --- Table: Final standings ---
    st.subheader(t("current_standings"))
    standings = final_pts.reset_index()
    standings.columns = ["Rider", "Points"]
    standings.insert(0, "Pos", standings["Points"].rank(ascending=False, method="min").astype(int))
    st.caption(t("home_championship_method"))

    def hl_champ(row):
        fills = {1: "#FFF4CC", 2: "#E8E8E8", 3: "#F5DEB3"}
        bg = fills.get(row.Pos, "")
        return [f"background-color: {bg}; color: #1a1a1a; font-weight: bold"] * len(row) if bg else [""] * len(row)

    st.dataframe(standings.style.apply(hl_champ, axis=1),
                 width="stretch", hide_index=True, height=500)


# =====================================================================
# 🔧 RELIABILITY — races finished vs DNF per rider
# =====================================================================
elif viz == "🔧 Reliability":
    st.header(t("reliability_title"))
    st.caption(t("reliability_caption_text"))

    STATUS_MAP = {
        "INSTND": "Finished",
        "OUTSTND": "DNF",
        "NOTFINISHFIRST": "DNF Lap 1",
        "NOTSTARTED": "DNS",
    }

    sel_years = st.multiselect(t("seasons"), year_list, default=year_list[:3], key="rel_yrs")
    if not sel_years:
        st.info(t("select_season")); st.stop()

    ph = ",".join("?" * len(sel_years))
    rel = premier_q(f"""
        SELECT e.season_year, r.full_name AS rider, cl.status, COUNT(*) AS cnt
        FROM classifications cl
        JOIN sessions s ON cl.session_id = s.session_id
        JOIN events e ON s.event_id = e.event_id
        JOIN riders r ON cl.rider_id = r.rider_id
        WHERE e.season_year IN ({ph}) AND s.session_type = 'RAC'
        GROUP BY e.season_year, r.full_name, cl.status
    """, sel_years)

    if rel.empty:
        st.info(t("no_race_data_selected")); st.stop()

    rel["outcome"] = rel["status"].map(STATUS_MAP).fillna("Other")

    # Aggregate across selected years
    agg = rel.groupby(["rider", "outcome"])["cnt"].sum().reset_index()
    total = agg.groupby("rider")["cnt"].sum().reset_index().rename(columns={"cnt": "races"})
    finished = agg[agg["outcome"] == "Finished"].groupby("rider")["cnt"].sum().reset_index().rename(columns={"cnt": "finished"})
    summary = total.merge(finished, on="rider", how="left")
    summary["finished"] = summary["finished"].fillna(0).astype(int)
    summary["finish_pct"] = (summary["finished"] / summary["races"] * 100).round(1)
    summary = summary[summary["races"] >= 3].sort_values("finish_pct", ascending=True)

    # Stacked horizontal bar — Finished / DNF / DNF Lap 1 / DNS
    pivot = agg.pivot_table(index="rider", columns="outcome", values="cnt",
                            aggfunc="sum", fill_value=0).reset_index()
    # Ensure all columns exist
    for col in ["Finished", "DNF", "DNF Lap 1", "DNS"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["Total"] = pivot[["Finished", "DNF", "DNF Lap 1", "DNS"]].sum(axis=1)
    pivot = pivot[pivot["Total"] >= 3]
    pivot["DNF_total"] = pivot["DNF"] + pivot["DNF Lap 1"] + pivot["DNS"]
    pivot = pivot.sort_values("DNF_total", ascending=True)

    fig = px.bar(
        pivot, y="rider", x=["Finished", "DNF", "DNF Lap 1", "DNS"],
        orientation="h", barmode="stack",
        title=t("race_outcomes_title", years=', '.join(str(y) for y in sorted(sel_years))),
        labels={"value": t("races"), "rider": ""},
        color_discrete_map={"Finished": "#2ecc71", "DNF": "#e74c3c",
                            "DNF Lap 1": "#e67e22", "DNS": "#95a5a6"},
    )
    fig.update_layout(height=max(450, len(pivot) * 28), legend_title=t("outcome"))
    st.plotly_chart(fig, width="stretch")

    # Finish rate comparison per year (for riders with races in multiple years)
    if len(sel_years) > 1:
        st.subheader(t("finish_rate_by_season"))
        yearly = rel.copy()
        yearly["is_finished"] = (yearly["outcome"] == "Finished").astype(int) * yearly["cnt"]
        yr_agg = yearly.groupby(["season_year", "rider"]).agg(
            races=("cnt", "sum"), finished=("is_finished", "sum")).reset_index()
        yr_agg["finish_pct"] = (yr_agg["finished"] / yr_agg["races"] * 100).round(1)
        # Only show riders with races in at least 2 selected years
        multi_yr = yr_agg.groupby("rider")["season_year"].nunique()
        multi_yr = multi_yr[multi_yr >= 2].index.tolist()
        yr_agg = yr_agg[yr_agg["rider"].isin(multi_yr)]

        if not yr_agg.empty:
            # Heatmap: rider × year → finish %
            heat = yr_agg.pivot_table(index="rider", columns="season_year",
                                       values="finish_pct", aggfunc="first")
            avg_pct = heat.mean(axis=1).sort_values(ascending=False)
            heat = heat.loc[avg_pct.index]

            fig2 = go.Figure(data=go.Heatmap(
                z=heat.values,
                x=[str(c) for c in heat.columns],
                y=heat.index.tolist(),
                colorscale=[[0, "#e74c3c"], [0.5, "#f39c12"], [1.0, "#2ecc71"]],
                zmin=0, zmax=100,
                text=heat.map(lambda v: f"{int(v)}%" if pd.notna(v) else "").values,
                texttemplate="%{text}",
                hovertemplate="Rider: %{y}<br>Year: %{x}<br>Finish rate: %{z:.0f}%<extra></extra>",
            ))
            fig2.update_layout(
                title=t("finish_rate_heatmap_title"),
                height=max(400, len(heat) * 28),
                yaxis=dict(autorange="reversed"),
                xaxis=dict(type="category"),
            )
            st.plotly_chart(fig2, width="stretch")


# =====================================================================
# 🏢 TEAMS & CONSTRUCTORS
# =====================================================================
elif viz == "🏢 Teams & Constructors":
    st.header(t("teams_constructors_header", year=selected_year))

    tc_tab = st.radio(t("view_label"), [t("teams_label"), t("constructors_label")], horizontal=True)

    if tc_tab == t("teams_label"):
        st.subheader(t("team_performance"))

        team_pts = premier_q("""
            SELECT t.team_name AS Team, r.full_name AS Rider,
                SUM(c.points) AS Points
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
            WHERE e.season_year = ? AND s.session_type IN ('RAC', 'SPR') AND c.points > 0
            GROUP BY t.team_name, r.full_name
            ORDER BY t.team_name, Points DESC
        """, [selected_year])

        if team_pts.empty:
            st.info(t("no_data")); st.stop()

        # Stacked bar: team total with rider breakdown
        team_totals = team_pts.groupby("Team")["Points"].sum().sort_values(ascending=False)
        team_order = team_totals.index.tolist()
        team_pts["Team"] = pd.Categorical(team_pts["Team"], categories=team_order, ordered=True)
        team_pts = team_pts.sort_values(["Team", "Points"], ascending=[True, False])

        fig = px.bar(team_pts, x="Team", y="Points", color="Rider", barmode="stack",
                     title=t("team_points_title", year=selected_year),
                     labels={"Points": t("total_points_label")})
        fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig, width="stretch")

        # Team championship progression
        st.subheader(t("team_progression"))
        team_prog = premier_q("""
            SELECT e.short_name, e.date_end, t.team_name AS Team,
                SUM(c.points) AS pts
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
            WHERE e.season_year = ? AND s.session_type IN ('RAC', 'SPR') AND c.points > 0
            GROUP BY e.short_name, e.date_end, t.team_name
            ORDER BY e.date_end
        """, [selected_year])

        if not team_prog.empty:
            evts = team_prog.drop_duplicates("short_name").sort_values("date_end")["short_name"].tolist()
            agg = team_prog.groupby(["short_name", "Team"])["pts"].sum().reset_index()
            agg["eo"] = agg["short_name"].map({e: i for i, e in enumerate(evts)})
            agg = agg.sort_values("eo")
            agg["cum"] = agg.groupby("Team")["pts"].cumsum()
            top_teams = agg.groupby("Team")["cum"].max().nlargest(8).index.tolist()

            fig2 = px.line(agg[agg["Team"].isin(top_teams)], x="short_name", y="cum",
                           color="Team", markers=True,
                           title=t("team_pts_progression_title", year=selected_year),
                           labels={"short_name": t("grand_prix_label"), "cum": t("cumulative_points_label")},
                           category_orders={"short_name": evts})
            fig2.update_layout(height=450, xaxis_tickangle=-45)
            st.plotly_chart(fig2, width="stretch")

        # Team results table
        st.subheader(t("team_standings"))
        team_table = team_totals.reset_index()
        team_table.columns = ["Team", "Points"]
        team_table.insert(0, "Pos", range(1, len(team_table) + 1))
        team_table["Points"] = team_table["Points"].astype(int)
        st.dataframe(team_table, width="stretch", hide_index=True)

    else:  # Constructors
        st.subheader(t("constructor_performance"))
        st.caption(t("constructor_performance_caption"))

        const_data = premier_q("""
            SELECT t.constructor AS Constructor, r.full_name AS Rider,
                SUM(c.points) AS Points
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
            WHERE e.season_year = ? AND s.session_type IN ('RAC', 'SPR')
                AND t.constructor IS NOT NULL
            GROUP BY t.constructor, r.full_name
        """, [selected_year])

        if const_data.empty:
            st.info(t("no_data")); st.stop()

        # Compute avg points per rider per constructor
        const_avg = const_data.groupby("Constructor").agg(
            Total_Points=("Points", "sum"),
            Riders=("Rider", "nunique"),
            Avg_Per_Rider=("Points", "mean"),
        ).reset_index().sort_values("Avg_Per_Rider", ascending=False)
        const_avg["Avg_Per_Rider"] = const_avg["Avg_Per_Rider"].round(1)

        # Side-by-side: avg vs total
        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.bar(const_avg, x="Constructor", y="Avg_Per_Rider",
                         text="Avg_Per_Rider",
                         title=t("avg_points_per_rider"),
                         color="Constructor")
            fig.update_layout(height=400, showlegend=False)
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, width="stretch")

        with col_r:
            fig2 = px.bar(const_avg, x="Constructor", y="Total_Points",
                          text="Total_Points",
                          title=t("total_points_all_riders"),
                          color="Constructor")
            fig2.update_layout(height=400, showlegend=False)
            fig2.update_traces(textposition="outside")
            st.plotly_chart(fig2, width="stretch")

        # Rider breakdown per constructor
        st.subheader(t("rider_points_by_constructor"))
        const_order = const_avg["Constructor"].tolist()
        const_data["Constructor"] = pd.Categorical(const_data["Constructor"],
                                                    categories=const_order, ordered=True)
        fig3 = px.bar(const_data.sort_values(["Constructor", "Points"], ascending=[True, False]),
                      x="Constructor", y="Points", color="Rider", barmode="stack",
                      title=t("constructor_points_breakdown", year=selected_year))
        fig3.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig3, width="stretch")

        # Constructor comparison across years
        st.subheader(t("constructor_avg_across_seasons"))
        const_multi = premier_q("""
            SELECT e.season_year AS Year, t.constructor AS Constructor,
                AVG(sub.rider_pts) AS Avg_Per_Rider
            FROM (
                SELECT e2.season_year, t2.constructor, r2.rider_id,
                    SUM(c2.points) AS rider_pts
                FROM classifications c2
                JOIN sessions s2 ON c2.session_id = s2.session_id
                JOIN events e2 ON s2.event_id = e2.event_id
                JOIN riders r2 ON c2.rider_id = r2.rider_id
                LEFT JOIN teams t2 ON c2.team_id = t2.team_id AND t2.season_year = e2.season_year
                WHERE s2.session_type IN ('RAC', 'SPR') AND t2.constructor IS NOT NULL
                GROUP BY e2.season_year, t2.constructor, r2.rider_id
            ) sub
            JOIN events e ON e.season_year = sub.season_year
            JOIN teams t ON t.constructor = sub.constructor AND t.season_year = sub.season_year
            GROUP BY e.season_year, t.constructor
            ORDER BY e.season_year
        """)

        if not const_multi.empty:
            const_multi["Avg_Per_Rider"] = const_multi["Avg_Per_Rider"].round(1)
            const_multi["Year"] = const_multi["Year"].astype(str)
            fig4 = px.line(const_multi, x="Year", y="Avg_Per_Rider", color="Constructor",
                           markers=True,
                           title=t("constructor_avg_yoy_title"),
                           labels={"Avg_Per_Rider": t("avg_pts_rider_label")})
            fig4.update_layout(height=450)
            st.plotly_chart(fig4, width="stretch")

        # Summary table
        st.subheader(t("constructor_summary"))
        const_avg_display = const_avg[["Constructor", "Riders", "Avg_Per_Rider", "Total_Points"]].copy()
        const_avg_display.columns = ["Constructor", "Riders", "Avg Pts/Rider", "Total Points"]
        const_avg_display["Total Points"] = const_avg_display["Total Points"].astype(int)
        st.dataframe(const_avg_display, width="stretch", hide_index=True)


# =====================================================================
# 🏁 GRID ADVANTAGE
# =====================================================================
elif viz == "🏁 Grid Advantage":
    st.header(t("grid_advantage_header"))
    st.caption(t("grid_advantage_caption"))

    sel_yrs = st.multiselect(t("seasons"), year_list, default=year_list, key="grid_yrs")
    race_type = st.radio(t("race_type_label"), [t("main_race"), t("sprint_race"), t("both")], horizontal=True)

    if not sel_yrs:
        st.info(t("select_season")); st.stop()

    stype_filter = {t("main_race"): "('RAC')", t("sprint_race"): "('SPR')", t("both"): "('RAC','SPR')"}[race_type]
    ph = ",".join("?" * len(sel_yrs))

    grid_data = premier_q(f"""
        SELECT grid.season_year, grid.event_id, grid.rider_id, grid.grid_pos, race.finish_pos
        FROM (
            SELECT e.season_year, e.event_id, c.rider_id, c.position AS grid_pos
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            WHERE s.session_type = 'Q' AND s.session_number = 2
                AND e.season_year IN ({ph}) AND c.position IS NOT NULL
        ) grid
        JOIN (
            SELECT e.event_id, c.rider_id, c.position AS finish_pos
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            WHERE s.session_type IN {stype_filter}
                AND e.season_year IN ({ph}) AND c.position IS NOT NULL
        ) race ON grid.event_id = race.event_id AND grid.rider_id = race.rider_id
    """, sel_yrs + sel_yrs)

    if grid_data.empty:
        st.info(t("no_grid_race_data")); st.stop()

    col1, col2 = st.columns(2)
    with col1:
        top_x = st.slider(t("finish_top_x"), 1, 10, 3)
    with col2:
        max_y = st.slider(t("starting_from_y"), 1, 22, 10)

    # --- Key metric tile ---
    starters_xy = grid_data[grid_data["grid_pos"] <= max_y]
    total_xy = len(starters_xy)
    in_top_xy = len(starters_xy[starters_xy["finish_pos"] <= top_x])
    pct_xy = round(in_top_xy / total_xy * 100, 1) if total_xy > 0 else 0

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1a5276, #2e86c1); border-radius: 12px;
         padding: 20px; text-align: center; margin: 10px 0;">
        <span style="font-size: 3em; font-weight: bold; color: white;">{pct_xy}%</span><br>
        <span style="font-size: 1.1em; color: #d5e8f0;">
            {t("grid_pct_of_riders", max_y=max_y, top_x=top_x)}
        </span><br>
        <span style="font-size: 0.9em; color: #aed6f1;">
            {t("grid_pct_starts", count=in_top_xy, total=total_xy)}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # --- Bar chart: % for each starting-from-top-Y ---
    results = []
    for grid_pos in range(1, max_y + 1):
        starters = grid_data[grid_data["grid_pos"] <= grid_pos]
        total = len(starters)
        in_top = len(starters[starters["finish_pos"] <= top_x])
        pct = round(in_top / total * 100, 1) if total > 0 else 0
        results.append({"Starting from top": grid_pos, "pct": pct, "Count": total, "In top": in_top})

    res_df = pd.DataFrame(results)

    fig = px.bar(res_df, x="Starting from top", y="pct", text="pct",
                 title=t("grid_pct_title", top_x=top_x),
                 color="pct", color_continuous_scale="Greens",
                 labels={"pct": t("finished_top_x_pct", top_x=top_x)})
    fig.update_layout(height=450, coloraxis_showscale=False, xaxis=dict(dtick=1))
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    st.plotly_chart(fig, width="stretch")

    # --- Heatmap: grid position vs finish position (raw counts) ---
    st.subheader(t("grid_finish_frequency"))
    st.caption(t("grid_finish_frequency_caption"))
    heat = grid_data[(grid_data["grid_pos"] <= 15) & (grid_data["finish_pos"] <= 15)].copy()
    if not heat.empty:
        heat_pivot = heat.groupby(["grid_pos", "finish_pos"]).size().reset_index(name="count")
        heat_matrix = heat_pivot.pivot_table(index="grid_pos", columns="finish_pos",
                                              values="count", fill_value=0)
        fig2 = go.Figure(data=go.Heatmap(
            z=heat_matrix.values,
            x=[f"P{int(c)}" for c in heat_matrix.columns],
            y=[f"Grid {int(r)}" for r in heat_matrix.index],
            colorscale="YlOrRd",
            text=heat_matrix.values, texttemplate="%{text}",
            hovertemplate="Grid: %{y}<br>Finish: %{x}<br>Count: %{z}<extra></extra>",
        ))
        fig2.update_layout(
            height=500, title=t("grid_vs_finish_freq_title"),
            xaxis_title=t("finish_position"), yaxis_title=t("grid_position"),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig2, width="stretch")

    # --- Heatmap: % finishing in top X when starting from top Y ---
    st.subheader(t("conversion_rate_subheader"))
    st.caption(t("conversion_rate_caption"))
    max_hx = min(10, top_x + 5)
    max_hy = min(22, max_y + 5)
    conv_data = []
    for y in range(1, max_hy + 1):
        row = []
        for x in range(1, max_hx + 1):
            s = grid_data[grid_data["grid_pos"] <= y]
            t = len(s)
            i = len(s[s["finish_pos"] <= x])
            row.append(round(i / t * 100, 1) if t > 0 else 0)
        conv_data.append(row)

    conv_matrix = np.array(conv_data)
    fig3 = go.Figure(data=go.Heatmap(
        z=conv_matrix,
        x=[f"Top {x}" for x in range(1, max_hx + 1)],
        y=[f"Grid ≤ {y}" for y in range(1, max_hy + 1)],
        colorscale=[[0, "#fff5f0"], [0.5, "#fcbba1"], [1.0, "#a50f15"]],
        zmin=0, zmax=100,
        text=conv_matrix.astype(str) + "%",
        texttemplate="%{text}",
        hovertemplate="Starting from: %{y}<br>Finishing in: %{x}<br>Rate: %{z:.1f}%<extra></extra>",
    ))
    fig3.update_layout(
        height=max(450, max_hy * 28),
        title=t("conversion_rate_title"),
        xaxis_title=t("finish_pos_top_x"),
        yaxis_title=t("grid_pos_top_y"),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig3, width="stretch")

    # Trend: has grid advantage changed over the years?
    if len(sel_yrs) > 1:
        st.subheader(t("grid_trend_subheader"))
        st.caption(t("grid_trend_caption", top_x=top_x))
        trend = []
        for yr in sorted(sel_yrs):
            yr_data = grid_data[grid_data["season_year"] == yr]
            top3_start = yr_data[yr_data["grid_pos"] <= 3]
            total = len(top3_start)
            in_top = len(top3_start[top3_start["finish_pos"] <= top_x])
            pct = round(in_top / total * 100, 1) if total > 0 else 0
            trend.append({"Year": str(int(yr)), "Top 3 grid → top " + str(top_x) + " %": pct})
        trend_df = pd.DataFrame(trend)
        trend_col = f"Top 3 grid → top {top_x} %"
        fig4 = px.line(trend_df, x="Year", y=trend_col, markers=True,
                       title=t("front_row_conversion_title", top_x=top_x),
                       text=trend_col)
        fig4.update_traces(texttemplate="%{text}%", textposition="top center")
        fig4.update_layout(height=380, xaxis=dict(type="category"))
        st.plotly_chart(fig4, width="stretch")


# =====================================================================
# 🏟 CIRCUITS
# =====================================================================
elif viz == "🏟 Circuits":
    st.header(t("circuit_analysis_header"))

    # Load all circuit + race data
    circuit_data = premier_q("""
        SELECT e.circuit_name, e.short_name, e.circuit_place, e.country_name,
            e.season_year, r.full_name AS rider, t.constructor,
            COALESCE(ta.canonical_name, t.team_name) AS team_name,
            c.position, c.points, c.best_lap_time, c.top_speed
        FROM classifications c
        JOIN sessions s ON c.session_id = s.session_id
        JOIN events e ON s.event_id = e.event_id
        JOIN riders r ON c.rider_id = r.rider_id
        LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
        LEFT JOIN team_aliases ta ON t.team_name = ta.team_name
        WHERE s.session_type = 'RAC'
    """)
    if circuit_data.empty:
        st.info(t("no_race_data")); st.stop()

    circuits = circuit_data.drop_duplicates("short_name").sort_values("circuit_name")
    circuit_labels = {r.short_name: f"{r.short_name} — {r.circuit_name}, {r.circuit_place}"
                      for _, r in circuits.iterrows()}
    circuit_list = list(circuit_labels.keys())

    sel_circuit = st.sidebar.selectbox(t("circuit_label"), circuit_list,
                                       format_func=lambda x: circuit_labels[x])

    cd = circuit_data[circuit_data["short_name"] == sel_circuit]
    circuit_info = circuits[circuits["short_name"] == sel_circuit].iloc[0]

    st.subheader(f"📍 {circuit_info.circuit_name}")
    st.caption(f"{circuit_info.circuit_place}, {circuit_info.country_name} · "
               f"{t('seasons_in_db', seasons=', '.join(str(int(y)) for y in sorted(cd['season_year'].unique())))}")

    # --- Key stats ---
    n_races = cd[cd["position"] == 1].shape[0]
    unique_winners = cd[cd["position"] == 1]["rider"].nunique()
    unique_constructors = cd[cd["position"] == 1]["constructor"].dropna().nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric(t("races_in_db"), n_races)
    c2.metric(t("different_winners"), unique_winners)
    c3.metric(t("winning_constructors"), unique_constructors)

    st.divider()

    # --- Top winners ---
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader(t("top_winners_riders"))
        wins = cd[cd["position"] == 1].groupby("rider").size().sort_values(ascending=False).reset_index()
        wins.columns = ["Rider", "Wins"]
        if not wins.empty:
            fig = px.bar(wins.head(10), x="Rider", y="Wins", text="Wins",
                         color="Wins", color_continuous_scale="YlOrRd")
            fig.update_layout(height=380, coloraxis_showscale=False, xaxis_tickangle=-45,
                              yaxis=dict(range=[0, wins["Wins"].max() * 1.3]))
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, width="stretch")

    with col_r:
        st.subheader(t("top_winners_constructors"))
        const_wins = cd[cd["position"] == 1]["constructor"].dropna().value_counts().reset_index()
        const_wins.columns = ["Constructor", "Wins"]
        if not const_wins.empty:
            fig = px.pie(const_wins, values="Wins", names="Constructor",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=380)
            st.plotly_chart(fig, width="stretch")

    st.divider()

    # --- Race winners history ---
    st.subheader(t("race_winners_by_year"))
    winners = cd[cd["position"] == 1][["season_year", "rider", "constructor", "team_name"]].copy()
    winners["Year"] = winners["season_year"].astype(int)
    winners = winners.sort_values("Year")
    winners_display = winners[["Year", "rider", "team_name", "constructor"]].copy()
    winners_display.columns = ["Year", "Winner", "Team", "Constructor"]
    st.dataframe(winners_display, width="stretch", hide_index=True)

    st.divider()

    # --- Podium frequency ---
    st.subheader(t("most_podiums_circuit"))
    podiums = cd[cd["position"].isin([1, 2, 3])].copy()
    pod_count = podiums.groupby(["rider", "position"]).size().reset_index(name="count")
    pod_pivot = pod_count.pivot_table(index="rider", columns="position", values="count",
                                       aggfunc="sum", fill_value=0).reset_index()
    pod_pivot.columns = ["Rider"] + [f"P{int(c)}" for c in pod_pivot.columns[1:]]
    for c in ["P1", "P2", "P3"]:
        if c not in pod_pivot.columns:
            pod_pivot[c] = 0
    pod_pivot["Total"] = pod_pivot["P1"] + pod_pivot["P2"] + pod_pivot["P3"]
    pod_pivot = pod_pivot.sort_values("Total", ascending=False)

    fig = px.bar(pod_pivot.head(10), x="Rider", y=["P1", "P2", "P3"],
                 title=t("podiums_circuit_title"),
                 color_discrete_map={"P1": "#FFD700", "P2": "#C0C0C0", "P3": "#CD7F32"},
                 barmode="stack")
    fig.update_layout(height=420, xaxis_tickangle=-45)
    st.plotly_chart(fig, width="stretch")

    st.divider()

    # --- Lap time evolution (from laps table, not classification) ---
    st.subheader(t("winning_pace_evolution"))
    bl = premier_q("""
        SELECT e.season_year, r.full_name AS rider, MIN(l.lap_time) AS best_lap
        FROM laps l
        JOIN sessions s ON l.session_id = s.session_id
        JOIN events e ON s.event_id = e.event_id
        JOIN riders r ON l.rider_id = r.rider_id
        JOIN classifications c ON c.session_id = s.session_id AND c.rider_id = l.rider_id
        WHERE s.session_type = 'RAC' AND e.short_name = ? AND c.position = 1
            AND l.is_pit = 0
        GROUP BY e.season_year, r.full_name
        ORDER BY e.season_year
    """, [sel_circuit])
    if not bl.empty:
        bl["sec"] = bl["best_lap"].apply(lap_to_sec)
        bl = bl.dropna(subset=["sec"])
    if not bl.empty:
        bl["Year"] = bl["season_year"].astype(str)
        fig = px.scatter(bl, x="Year", y="sec", text="rider",
                         title=t("winner_best_lap_title"),
                         labels={"sec": t("best_lap_s")}, color="rider")
        fig.update_traces(marker=dict(size=12), textposition="top center", textfont_size=9)
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info(t("no_data"))

    # --- Top speed evolution (from laps table) ---
    st.subheader(t("top_speed_circuit"))
    ts = premier_q("""
        SELECT e.season_year, MAX(l.speed_kmh) AS max_speed, AVG(l.speed_kmh) AS avg_speed
        FROM laps l
        JOIN sessions s ON l.session_id = s.session_id
        JOIN events e ON s.event_id = e.event_id
        WHERE s.session_type = 'RAC' AND e.short_name = ?
            AND l.speed_kmh IS NOT NULL AND l.speed_kmh > 0
        GROUP BY e.season_year
        ORDER BY e.season_year
    """, [sel_circuit])
    if not ts.empty:
        ts["Year"] = ts["season_year"].astype(str)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ts["Year"], y=ts["max_speed"],
                                  mode="lines+markers", name=t("max_speed_trace"),
                                  marker=dict(size=10)))
        fig.add_trace(go.Scatter(x=ts["Year"], y=ts["avg_speed"].round(1),
                                  mode="lines+markers", name=t("avg_speed_trace"),
                                  marker=dict(size=8), line=dict(dash="dash")))
        fig.update_layout(height=380, title=t("top_speed_evolution_title"),
                          yaxis_title=t("kmh"), hovermode="x unified",
                          yaxis=dict(range=[ts[["max_speed", "avg_speed"]].min().min() - 5,
                                            ts["max_speed"].max() + 5]))
        st.plotly_chart(fig, width="stretch")
    else:
        st.info(t("no_data"))

    st.divider()

    # --- Points scored at this circuit ---
    st.subheader(t("total_points_circuit"))
    pts = cd.groupby("rider")["points"].sum().sort_values(ascending=False).reset_index()
    pts.columns = ["Rider", "Points"]
    pts["Points"] = pts["Points"].astype(int)
    pts = pts[pts["Points"] > 0]
    fig = px.bar(pts.head(12), x="Rider", y="Points", text="Points",
                 color="Points", color_continuous_scale="Greens")
    fig.update_layout(height=400, coloraxis_showscale=False, xaxis_tickangle=-45,
                      yaxis=dict(range=[0, pts["Points"].head(1).values[0] * 1.2]))
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, width="stretch")

    # --- Competitiveness at this circuit ---
    st.subheader(t("circuit_competitiveness"))
    winners_per_yr = cd[cd["position"] == 1].groupby("season_year")["rider"].first().reset_index()
    repeat_winners = winners_per_yr["rider"].value_counts()
    pct_repeat = round((repeat_winners > 1).sum() / len(repeat_winners) * 100, 1) if len(repeat_winners) > 0 else 0
    avg_pos_range = cd.groupby("season_year").apply(
        lambda g: g[g["position"] <= 5]["position"].max() - g[g["position"] <= 5]["position"].min()
        if len(g[g["position"] <= 5]) > 0 else 0
    )

    c1, c2 = st.columns(2)
    c1.metric(t("repeat_winners_pct"), f"{pct_repeat}%",
              help=t("repeat_winners_help"))
    c2.metric(t("different_podium_riders"),
              cd[cd["position"].isin([1, 2, 3])]["rider"].nunique())


# =====================================================================
# 🏅 PILOT RANKINGS
# =====================================================================
elif viz == "🏅 Pilot Rankings":
    st.header(t("pilot_rankings_header"))
    st.caption(t("pilot_rankings_caption"))

    # Load comprehensive rider stats
    pstats = premier_q("""
        SELECT r.full_name AS rider, r.nationality,
            COUNT(CASE WHEN s.session_type = 'RAC' THEN 1 END) AS race_starts,
            COUNT(CASE WHEN s.session_type = 'SPR' THEN 1 END) AS sprint_starts,
            COUNT(CASE WHEN s.session_type = 'RAC' AND c.position = 1 THEN 1 END) AS race_wins,
            COUNT(CASE WHEN s.session_type = 'SPR' AND c.position = 1 THEN 1 END) AS sprint_wins,
            COUNT(CASE WHEN s.session_type = 'RAC' AND c.position <= 3 THEN 1 END) AS race_podiums,
            COUNT(CASE WHEN s.session_type = 'SPR' AND c.position <= 3 THEN 1 END) AS sprint_podiums,
            COUNT(CASE WHEN s.session_type = 'Q' AND s.session_number = 2 AND c.position = 1 THEN 1 END) AS poles,
            COUNT(CASE WHEN s.session_type = 'RAC' AND c.status = 'INSTND' THEN 1 END) AS race_finishes,
            COUNT(CASE WHEN s.session_type = 'RAC' AND c.status IN ('OUTSTND','NOTFINISHFIRST') THEN 1 END) AS dnfs,
            SUM(CASE WHEN s.session_type IN ('RAC','SPR') THEN c.points ELSE 0 END) AS total_pts,
            COUNT(DISTINCT e.season_year) AS seasons,
            MIN(e.season_year) AS first_year,
            MAX(e.season_year) AS last_year
        FROM classifications c
        JOIN sessions s ON c.session_id = s.session_id
        JOIN events e ON s.event_id = e.event_id
        JOIN riders r ON c.rider_id = r.rider_id
        GROUP BY r.full_name, r.nationality
    """)
    if pstats.empty:
        st.info(t("no_data")); st.stop()

    # Compute championships won per rider
    champs = premier_q("""
        SELECT rider, COUNT(*) AS championships FROM (
            SELECT e.season_year, r.full_name AS rider, SUM(c.points) AS pts,
                RANK() OVER (PARTITION BY e.season_year ORDER BY SUM(c.points) DESC) AS rnk
            FROM classifications c JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE s.session_type IN ('RAC','SPR')
            GROUP BY e.season_year, r.full_name
            HAVING SUM(c.points) > 0
        ) sub WHERE rnk = 1 GROUP BY rider
    """)
    champ_map = dict(zip(champs["rider"], champs["championships"])) if not champs.empty else {}
    pstats["championships"] = pstats["rider"].map(champ_map).fillna(0).astype(int)

    pstats["total_pts"] = pstats["total_pts"].astype(int)
    pstats["max_pts"] = pstats["race_starts"] * 25 + pstats["sprint_starts"] * 12
    pstats["pts_pct"] = (pstats["total_pts"] / pstats["max_pts"].replace(0, 1) * 100).round(1)
    pstats["win_pct"] = (pstats["race_wins"] / pstats["race_starts"].replace(0, 1) * 100).round(1)
    pstats["podium_pct"] = (pstats["race_podiums"] / pstats["race_starts"].replace(0, 1) * 100).round(1)
    pstats["finish_pct"] = (pstats["race_finishes"] / pstats["race_starts"].replace(0, 1) * 100).round(1)
    pstats["years"] = pstats["first_year"].astype(int).astype(str) + "–" + pstats["last_year"].astype(int).astype(str)

    ranking = st.selectbox(t("rank_by"), [
        t("ranking_championships_won"), t("ranking_race_wins"), t("ranking_sprint_wins"), t("ranking_total_wins"),
        t("ranking_race_podiums"), t("ranking_pole_positions"), t("ranking_total_points"),
        t("ranking_points_efficiency"), t("ranking_win_rate"), t("ranking_podium_rate"),
        t("ranking_race_starts"), t("ranking_finish_rate"),
    ])

    ranking_descriptions = {
        t("ranking_championships_won"): t("ranking_desc_championships"),
        t("ranking_race_wins"): t("ranking_desc_race_wins"),
        t("ranking_sprint_wins"): t("ranking_desc_sprint_wins"),
        t("ranking_total_wins"): t("ranking_desc_total_wins"),
        t("ranking_race_podiums"): t("ranking_desc_race_podiums"),
        t("ranking_pole_positions"): t("ranking_desc_poles"),
        t("ranking_total_points"): t("ranking_desc_total_points"),
        t("ranking_points_efficiency"): t("ranking_desc_points_efficiency"),
        t("ranking_win_rate"): t("ranking_desc_win_rate"),
        t("ranking_podium_rate"): t("ranking_desc_podium_rate"),
        t("ranking_race_starts"): t("ranking_desc_race_starts"),
        t("ranking_finish_rate"): t("ranking_desc_finish_rate"),
    }
    st.caption(ranking_descriptions.get(ranking, ""))

    col_map = {
        t("ranking_championships_won"): "championships",
        t("ranking_race_wins"): "race_wins", t("ranking_sprint_wins"): "sprint_wins",
        t("ranking_total_wins"): None,
        t("ranking_race_podiums"): "race_podiums", t("ranking_pole_positions"): "poles",
        t("ranking_total_points"): "total_pts", t("ranking_points_efficiency"): "pts_pct",
        t("ranking_win_rate"): "win_pct", t("ranking_podium_rate"): "podium_pct",
        t("ranking_race_starts"): "race_starts", t("ranking_finish_rate"): "finish_pct",
    }

    if ranking == t("ranking_total_wins"):
        pstats["total_wins"] = pstats["race_wins"] + pstats["sprint_wins"]
        sort_col = "total_wins"
    else:
        sort_col = col_map[ranking]

    # Filter: minimum race starts for rate-based rankings
    min_starts = 10 if "%" in ranking else 1
    filtered = pstats[pstats["race_starts"] >= min_starts].sort_values(sort_col, ascending=False)

    # Bar chart of top 15
    top15 = filtered.head(15)
    fig = px.bar(top15, x="rider", y=sort_col, text=sort_col,
                 title=t("top_pilots_by", ranking=ranking),
                 color=sort_col, color_continuous_scale="Viridis",
                 labels={"rider": "", sort_col: ranking})
    fig.update_layout(height=480, coloraxis_showscale=False, xaxis_tickangle=-45,
                      yaxis=dict(range=[0, top15[sort_col].max() * 1.2]))
    if "%" in ranking:
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
    else:
        fig.update_traces(textposition="outside")
    st.plotly_chart(fig, width="stretch")

    st.divider()

    # --- Comprehensive leaderboards side by side ---
    st.subheader(t("leaderboards"))

    lb0a, lb0b, lb0c = st.columns(3)
    with lb0a:
        st.markdown(t("lb_championships"))
        st.caption(t("lb_championships_caption"))
        ch = pstats[pstats["championships"] > 0].nlargest(10, "championships")[["rider", "championships"]].copy()
        ch.columns = ["Rider", "Titles"]
        st.dataframe(ch, hide_index=True, width="stretch")

    with lb0b:
        st.markdown(t("lb_race_wins"))
        st.caption(t("lb_race_wins_caption"))
        w = pstats.nlargest(10, "race_wins")[["rider", "race_wins"]].copy()
        w.columns = ["Rider", "Wins"]
        st.dataframe(w, hide_index=True, width="stretch")

    with lb0c:
        st.markdown(t("lb_sprint_wins"))
        st.caption(t("lb_sprint_wins_caption"))
        sw = pstats.nlargest(10, "sprint_wins")[["rider", "sprint_wins"]].copy()
        sw.columns = ["Rider", "Wins"]
        st.dataframe(sw, hide_index=True, width="stretch")

    lb1, lb2, lb3 = st.columns(3)
    with lb1:
        st.markdown(t("lb_poles"))
        st.caption(t("lb_poles_caption"))
        pp = pstats.nlargest(10, "poles")[["rider", "poles"]].copy()
        pp.columns = ["Rider", "Poles"]
        st.dataframe(pp, hide_index=True, width="stretch")

    lb4, lb5, lb6 = st.columns(3)
    with lb4:
        st.markdown(t("lb_podiums"))
        st.caption(t("lb_podiums_caption"))
        pd_lb = pstats.nlargest(10, "race_podiums")[["rider", "race_podiums"]].copy()
        pd_lb.columns = ["Rider", "Podiums"]
        st.dataframe(pd_lb, hide_index=True, width="stretch")

    with lb5:
        st.markdown(t("lb_efficiency"))
        st.caption(t("lb_efficiency_caption"))
        eff = pstats[pstats["race_starts"] >= 10].nlargest(10, "pts_pct")[["rider", "pts_pct"]].copy()
        eff.columns = ["Rider", "Pts %"]
        st.dataframe(eff, hide_index=True, width="stretch")

    with lb6:
        st.markdown(t("lb_finish_rate"))
        st.caption(t("lb_finish_rate_caption"))
        fr = pstats[pstats["race_starts"] >= 10].nlargest(10, "finish_pct")[["rider", "finish_pct"]].copy()
        fr.columns = ["Rider", "Finish %"]
        st.dataframe(fr, hide_index=True, width="stretch")

    st.divider()

    # --- Full stats table ---
    st.subheader(t("complete_pilot_stats"))
    full = pstats.sort_values("total_pts", ascending=False).copy()
    display_cols = ["rider", "nationality", "years", "seasons", "championships", "race_starts", "race_wins",
                    "sprint_wins", "race_podiums", "sprint_podiums", "poles", "dnfs",
                    "total_pts", "pts_pct", "win_pct", "podium_pct", "finish_pct"]
    display_names = ["Rider", "Nationality", "Years", "Seasons", "Titles", "Races", "Race Wins",
                     "Sprint Wins", "Race Podiums", "Sprint Podiums", "Poles", "DNFs",
                     "Points", "Pts %", "Win %", "Podium %", "Finish %"]
    full_display = full[display_cols].copy()
    full_display.columns = display_names
    st.dataframe(full_display, width="stretch", hide_index=True, height=600)


# =====================================================================
# 👤 PILOT PROFILE
# =====================================================================
elif viz == "👤 Pilot Profile":
    st.header(t("pilot_profile_header"))
    riders_all = premier_q(
        "SELECT DISTINCT full_name FROM riders r WHERE EXISTS "
        "(SELECT 1 FROM classifications c JOIN sessions s ON c.session_id = s.session_id "
        "WHERE c.rider_id = r.rider_id) ORDER BY full_name"
    )
    if riders_all.empty:
        st.info(t("no_riders")); st.stop()
    pilot = st.sidebar.selectbox(t("rider"), riders_all["full_name"].tolist())

    # Season filter with "All"
    pilot_years = premier_q("SELECT DISTINCT e.season_year FROM classifications c "
                    "JOIN sessions s ON c.session_id = s.session_id "
                    "JOIN events e ON s.event_id = e.event_id "
                    "JOIN riders r ON c.rider_id = r.rider_id "
                    "WHERE r.full_name = ? ORDER BY e.season_year DESC", [pilot])
    if pilot_years.empty:
        st.info(t("no_data_for_pilot", pilot=pilot)); st.stop()
    py_list = pilot_years["season_year"].tolist()
    yr_sel = st.sidebar.selectbox(t("season"), ["All"] + py_list, key="pp_yr")
    filter_year = None if yr_sel == "All" else yr_sel

    career = premier_q("""
        SELECT e.season_year, e.short_name, e.date_end, s.session_type, s.session_label,
            c.position, c.points, c.best_lap_time, c.top_speed, c.status,
            COALESCE(ta.canonical_name, t.team_name) AS team_name, t.constructor, e.circuit_name
        FROM classifications c
        JOIN sessions s ON c.session_id = s.session_id
        JOIN events e ON s.event_id = e.event_id
        JOIN riders r ON c.rider_id = r.rider_id
        LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
        LEFT JOIN team_aliases ta ON t.team_name = ta.team_name
        WHERE r.full_name = ? ORDER BY e.date_end, s.session_date""", [pilot])

    if career.empty:
        st.info(t("no_data_for_pilot", pilot=pilot)); st.stop()

    if filter_year:
        career = career[career["season_year"] == filter_year]

    races = career[career["session_type"] == "RAC"]
    sprints = career[career["session_type"] == "SPR"]
    race_sprint = career[career["session_type"].isin(["RAC", "SPR"])]
    seasons = sorted(career["season_year"].unique())

    # --- Key stats ---
    st.subheader(f"📋 {pilot}")

    n_races = len(races)
    n_sprints = len(sprints)
    wins = len(races[races["position"] == 1])
    sprint_wins = len(sprints[sprints["position"] == 1])
    podiums = len(races[races["position"].isin([1, 2, 3])])
    total_pts = race_sprint["points"].sum()
    dnfs = len(races[races["status"].isin(["OUTSTND", "NOTFINISHFIRST"])])
    dns = len(races[races["status"] == "NOTSTARTED"])
    finished = len(races[races["status"] == "INSTND"])
    finish_pct = round(finished / n_races * 100, 1) if n_races > 0 else 0

    # Max possible points: 25 per race, 12 per sprint (2023+ format)
    max_race_pts = n_races * 25
    max_sprint_pts = n_sprints * 12
    max_total_pts = max_race_pts + max_sprint_pts
    pts_pct = round(total_pts / max_total_pts * 100, 1) if max_total_pts > 0 else 0

    # Average finish position (races only, excluding DNF/DNS)
    valid_pos = races[races["position"].notna() & races["status"].isin(["INSTND"])]
    avg_pos = round(valid_pos["position"].mean(), 1) if not valid_pos.empty else None

    row1 = st.columns(6)
    row1[0].metric(t("seasons"), len(seasons))
    row1[1].metric(t("race_starts"), n_races)
    row1[2].metric(t("race_wins_label"), wins)
    row1[3].metric(t("podiums"), podiums)
    row1[4].metric(t("ranking_total_points"), f"{total_pts:.0f}")
    row1[5].metric(t("points_pct"), f"{pts_pct}%")

    row2 = st.columns(6)
    row2[0].metric(t("sprint_starts"), n_sprints)
    row2[1].metric(t("sprint_wins_label"), sprint_wins)
    row2[2].metric(t("dnf"), dnfs)
    row2[3].metric(t("dns"), dns)
    row2[4].metric(t("finish_rate"), f"{finish_pct}%")
    row2[5].metric(t("avg_pos"), avg_pos if avg_pos else "—")

    st.caption(t("profile_seasons_teams",
        seasons=', '.join(str(y) for y in seasons),
        teams=', '.join(career['team_name'].dropna().unique()),
        constructors=', '.join(career['constructor'].dropna().unique())))

    st.divider()

    # --- Race positions scatter (by season overlay) ---
    st.subheader(t("race_finishing_positions"))
    if not races.empty:
        rp = races.copy().sort_values("date_end")
        rp["year"] = rp["season_year"].astype(str)
        # Use event index within each year for proper X ordering
        rp["gp_label"] = rp["short_name"] + " '" + rp["year"].str[-2:]
        label_order = rp["gp_label"].tolist()
        fig = go.Figure()
        for yr in sorted(rp["year"].unique()):
            yr_data = rp[rp["year"] == yr]
            fig.add_trace(go.Scatter(
                x=yr_data["gp_label"], y=yr_data["position"],
                mode="lines+markers", name=yr,
                marker=dict(size=10),
                hovertemplate="%{x}<br>P%{y}<extra></extra>",
            ))
        max_pos = rp["position"].dropna().max()
        fig.update_layout(
            title=t("race_results_title", pilot=pilot),
            height=400, hovermode="x unified",
            yaxis=dict(autorange=False, dtick=1, title=t("position"),
                       range=[max_pos + 0.5, 0.5], tick0=1),
            xaxis=dict(title="", tickangle=-60, categoryorder="array", categoryarray=label_order),
        )
        st.plotly_chart(fig, width="stretch")

    # --- Points per season ---
    st.subheader(t("points_per_season"))
    pts_yr = race_sprint.groupby("season_year").agg(
        Points=("points", "sum"),
        Races=("season_year", lambda x: len(career[(career["season_year"].isin(x)) & (career["session_type"] == "RAC")].drop_duplicates("short_name"))),
    ).reset_index()
    # Simpler approach
    pts_yr = race_sprint.groupby("season_year")["points"].sum().reset_index()
    pts_yr.columns = ["Year", "Points"]
    pts_yr["Year"] = pts_yr["Year"].astype(str)
    pts_yr["Points"] = pts_yr["Points"].astype(int)
    if not pts_yr.empty:
        fig = px.bar(pts_yr, x="Year", y="Points", title=t("season_points_title", pilot=pilot),
                     text="Points", color="Points", color_continuous_scale="Greens")
        fig.update_layout(height=350, coloraxis_showscale=False)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, width="stretch")

    # --- Season-by-season detailed stats table ---
    st.subheader(t("season_statistics"))
    season_stats = []
    for yr in seasons:
        yr_races = races[races["season_year"] == yr]
        yr_sprints = sprints[sprints["season_year"] == yr]
        yr_all = race_sprint[race_sprint["season_year"] == yr]
        yr_finished = yr_races[yr_races["status"] == "INSTND"]
        yr_wins = len(yr_races[yr_races["position"] == 1])
        yr_podiums = len(yr_races[yr_races["position"].isin([1, 2, 3])])
        yr_sprint_wins = len(yr_sprints[yr_sprints["position"] == 1])
        yr_sprint_podiums = len(yr_sprints[yr_sprints["position"].isin([1, 2, 3])])
        yr_pts = yr_all["points"].sum()
        yr_max = len(yr_races) * 25 + len(yr_sprints) * 12
        yr_avg = round(yr_finished["position"].mean(), 1) if not yr_finished.empty else None
        yr_dnf = len(yr_races[yr_races["status"].isin(["OUTSTND", "NOTFINISHFIRST"])])
        team = yr_all["team_name"].dropna().unique()
        row = {
            "Year": int(yr),
            "Team": team[0] if len(team) > 0 else "",
            "Races": len(yr_races),
            "Wins": yr_wins,
            "Podiums": yr_podiums,
        }
        if len(yr_sprints) > 0:
            row["Sprints"] = len(yr_sprints)
            row["Sprint Wins"] = yr_sprint_wins
            row["Sprint Podiums"] = yr_sprint_podiums
        row.update({
            "DNFs": yr_dnf,
            "Points": int(yr_pts),
            "Max Pts": int(yr_max),
            "Pts %": round(yr_pts / yr_max * 100, 1) if yr_max > 0 else 0,
            "Avg Pos": yr_avg if yr_avg else "",
        })
        season_stats.append(row)
    if season_stats:
        st.dataframe(pd.DataFrame(season_stats), width="stretch", hide_index=True)

    st.divider()

    # --- Best lap evolution ---
    st.subheader(t("best_lap_evolution"))
    bl = races[races["best_lap_time"].notna()].copy()
    bl["sec"] = bl["best_lap_time"].apply(lap_to_sec)
    bl = bl.dropna(subset=["sec"]).sort_values("date_end")
    if not bl.empty:
        bl["year"] = bl["season_year"].astype(str)
        bl["label"] = bl["short_name"] + " " + bl["year"]
        fig = px.scatter(bl, x="label", y="sec", color="year",
                         title=t("race_best_laps_title", pilot=pilot), labels={"label": "", "sec": t("seconds_label")},
                         category_orders={"label": bl["label"].tolist()})
        fig.update_traces(marker=dict(size=8))
        fig.update_layout(height=400, xaxis_tickangle=-60)
        st.plotly_chart(fig, width="stretch")

    # --- Top speed trend ---
    st.subheader(t("top_speed_trend"))
    ts = races[races["top_speed"].notna()].copy().sort_values("date_end")
    if not ts.empty:
        ts["label"] = ts["short_name"] + " " + ts["season_year"].astype(str)
        fig = px.line(ts, x="label", y="top_speed", markers=True,
                      title=t("race_top_speeds_title", pilot=pilot), labels={"label": "", "top_speed": t("kmh")},
                      category_orders={"label": ts["label"].tolist()})
        fig.update_layout(height=350, xaxis_tickangle=-60)
        st.plotly_chart(fig, width="stretch")

    st.divider()

    # --- Head-to-head ---
    st.subheader(t("head_to_head"))
    others = premier_q(
        "SELECT DISTINCT full_name FROM riders r WHERE full_name != ? AND EXISTS "
        "(SELECT 1 FROM classifications c JOIN sessions s ON c.session_id = s.session_id "
        "WHERE c.rider_id = r.rider_id) ORDER BY full_name", [pilot]
    )
    if not others.empty:
        rival = st.selectbox(t("compare_with"), others["full_name"].tolist())
        rival_races = premier_q("""
            SELECT e.season_year, e.short_name, e.date_end, c.position
            FROM classifications c JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE r.full_name = ? AND s.session_type = 'RAC' ORDER BY e.date_end""", [rival])
        p1 = races[["season_year", "short_name", "date_end", "position"]].rename(columns={"position": "pos1"})
        p2 = rival_races[["season_year", "short_name", "date_end", "position"]].rename(columns={"position": "pos2"})
        mg = p1.merge(p2, on=["season_year", "short_name", "date_end"]).sort_values("date_end")
        if not mg.empty:
            mg["label"] = mg["short_name"] + " " + mg["season_year"].astype(str)
            label_order = mg["label"].tolist()
            mg["winner"] = mg.apply(lambda r: pilot if r.pos1 < r.pos2 else rival if r.pos2 < r.pos1 else "Tie", axis=1)
            wc = mg["winner"].value_counts()
            c1, c2, c3 = st.columns(3)
            c1.metric(pilot, wc.get(pilot, 0))
            c2.metric(t("ties"), wc.get("Tie", 0))
            c3.metric(rival, wc.get(rival, 0))
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=mg["label"], y=mg["pos1"], mode="lines+markers", name=pilot))
            fig.add_trace(go.Scatter(x=mg["label"], y=mg["pos2"], mode="lines+markers", name=rival))
            max_p = max(mg["pos1"].max(), mg["pos2"].max())
            fig.update_layout(title=t("pilot_vs_rival_title", pilot=pilot, rival=rival),
                              yaxis=dict(autorange=False, title=t("position"), dtick=1, range=[max_p + 0.5, 0.5], tick0=1),
                              xaxis=dict(tickangle=-60, categoryorder="array", categoryarray=label_order),
                              height=400, hovermode="x unified")
            st.plotly_chart(fig, width="stretch")


# =====================================================================
# 📈 CROSS-YEAR
# =====================================================================
elif viz == "📈 Cross-Year":
    st.header(t("cross_year_header"))
    st.caption(t("cross_year_caption"))

    cross = st.selectbox(t("chart_label"), [
        t("cross_bar_chart_race"),
        t("cross_bump_chart"),
        t("cross_championship_concentration"),
        t("cross_top_riders"),
        t("cross_team_evolution"),
        t("cross_constructor_evolution"),
        t("cross_rider_career"),
        t("cross_dnf_safety"),
        t("cross_pole_stats"),
        t("cross_qualifying_race"),
        t("cross_race_competitiveness"),
        t("cross_season_dominance"),
        t("cross_nationality_trends"),
        t("cross_circuit_pace"),
    ])

    # --- Animated Bar Chart Race ---
    if cross == t("cross_bar_chart_race"):
        st.subheader(t("bar_chart_race_title"))
        st.caption(t("bar_chart_race_caption"))

        race_metric = st.radio(t("metric"), [
            t("constructor_wins"), t("constructor_points"),
            t("rider_wins"), t("rider_points"),
        ], horizontal=True)

        from raceplotly.plots import barplot

        if race_metric in [t("constructor_wins"), t("constructor_points")]:
            is_wins = race_metric == t("constructor_wins")
            cdata = premier_q("""
                SELECT e.season_year, e.short_name, e.date_end, t.constructor AS Item,
                    COUNT(CASE WHEN c.position = 1 AND s.session_type = 'RAC' THEN 1 END) AS wins,
                    SUM(c.points) AS pts
                FROM classifications c
                JOIN sessions s ON c.session_id = s.session_id
                JOIN events e ON s.event_id = e.event_id
                LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
                WHERE s.session_type IN ('RAC','SPR') AND t.constructor IS NOT NULL
                GROUP BY e.season_year, e.short_name, e.date_end, t.constructor
                ORDER BY e.date_end
            """)
            if cdata.empty:
                st.info(t("no_data")); st.stop()
            val_col = "wins" if is_wins else "pts"

        else:
            is_wins = race_metric == t("rider_wins")
            cdata = premier_q("""
                SELECT e.season_year, e.short_name, e.date_end, r.full_name AS Item,
                    COUNT(CASE WHEN c.position = 1 AND s.session_type = 'RAC' THEN 1 END) AS wins,
                    SUM(c.points) AS pts
                FROM classifications c
                JOIN sessions s ON c.session_id = s.session_id
                JOIN events e ON s.event_id = e.event_id
                JOIN riders r ON c.rider_id = r.rider_id
                WHERE s.session_type IN ('RAC','SPR')
                GROUP BY e.season_year, e.short_name, e.date_end, r.full_name
                ORDER BY e.date_end
            """)
            if cdata.empty:
                st.info(t("no_data")); st.stop()
            val_col = "wins" if is_wins else "pts"

        # Compute cumulative per GP (finest granularity)
        cdata = cdata.sort_values("date_end")
        cdata["GP"] = cdata["short_name"] + " " + cdata["season_year"].astype(str)
        cdata["cumulative"] = cdata.groupby("Item")[val_col].cumsum()

        # Build ordered list of unique GPs
        gp_order = list(dict.fromkeys(cdata["GP"]))

        # Sample every N GPs based on slider
        n_step = st.slider(t("gps_per_frame"), min_value=1, max_value=20, value=5,
                           help=t("gps_per_frame_help"))
        sampled_gps = [gp_order[i] for i in range(0, len(gp_order), n_step)]
        # Always include the last GP
        if gp_order[-1] not in sampled_gps:
            sampled_gps.append(gp_order[-1])

        # Keep only sampled GPs — for each item, take the last cumulative value at or before each sample point
        gp_to_idx = {gp: i for i, gp in enumerate(gp_order)}
        cdata["_gp_idx"] = cdata["GP"].map(gp_to_idx)

        # Use zero-padded numeric IDs as Time column so raceplotly sorts correctly
        # (raceplotly uses np.sort which sorts alphabetically — "AUS" < "JPN" breaks chronological order)
        sampled_time_ids = [f"{i:04d} {gp}" for i, gp in enumerate(sampled_gps)]
        time_id_to_gp = dict(zip(sampled_time_ids, sampled_gps))

        rows = []
        all_items = cdata["Item"].unique()
        for item in all_items:
            item_data = cdata[cdata["Item"] == item].set_index("_gp_idx")["cumulative"]
            prev_val = 0
            for time_id, gp in zip(sampled_time_ids, sampled_gps):
                gp_idx = gp_to_idx[gp]
                valid = item_data[item_data.index <= gp_idx]
                val = int(valid.iloc[-1]) if not valid.empty else prev_val
                prev_val = val
                rows.append({"Item": item, "Value": val, "Time": time_id})

        plot_data = pd.DataFrame(rows)

        # Add Start frame (sorts before "0000" alphabetically)
        start = pd.DataFrame({"Item": all_items, "Value": 0, "Time": "0000 Start"})
        plot_data = pd.concat([start, plot_data], ignore_index=True)

        # Only keep top 20 items by final value
        top_items = plot_data.groupby("Item")["Value"].max().nlargest(20).index
        plot_data = plot_data[plot_data["Item"].isin(top_items)]

        # Assign consistent colors per item
        # Brand colors for known constructors (avoid very dark colors for text readability)
        CONSTRUCTOR_COLORS = {
            "Ducati": "#CC0000", "Honda": "#2E8B57", "Yamaha": "#0066CC",
            "KTM": "#FF6600", "Aprilia": "#666666", "Suzuki": "#00BCD4",
            "Kawasaki": "#00CC00", "APR": "#666666",
        }
        all_items = plot_data.groupby("Item")["Value"].max().sort_values(ascending=False).index.tolist()
        # Use bright/medium palettes — exclude very dark colors that hide black text
        palette = [c for c in (
            px.colors.qualitative.Plotly + px.colors.qualitative.Set2 +
            px.colors.qualitative.Pastel + px.colors.qualitative.Safe
        ) if c.lower() not in ("#000000", "#1a1a1a", "#2e2e2e", "#333333")]
        color_map = {}
        palette_idx = 0
        for item in all_items:
            if item in CONSTRUCTOR_COLORS:
                color_map[item] = CONSTRUCTOR_COLORS[item]
            else:
                color_map[item] = palette[palette_idx % len(palette)]
                palette_idx += 1

        # Add color column directly (raceplotly's dict handling is buggy)
        plot_data["color"] = plot_data["Item"].map(color_map)

        my_raceplot = barplot(
            plot_data,
            item_column="Item",
            value_column="Value",
            time_column="Time",
            item_color=None,
        )
        # Override the random colors with our fixed ones
        my_raceplot.df["color"] = my_raceplot.df["Item"].map(color_map)
        fig = my_raceplot.plot(
            title=race_metric,
            item_label="",
            value_label=t("cumulative_total"),
            time_label="Grand Prix",
            frame_duration=800,
            orientation="horizontal",
        )
        fig.update_layout(height=600, font=dict(color="#1a1a1a"),
                          yaxis=dict(showticklabels=True, tickfont=dict(size=12, color="#1a1a1a")),
                          xaxis=dict(tickformat="d"))

        # Fix text labels: show name + value, dark color, integer format
        def fix_traces(traces):
            for trace in traces:
                if hasattr(trace, "textfont"):
                    trace.textfont = dict(color="#1a1a1a", size=11)
                if hasattr(trace, "texttemplate") or hasattr(trace, "text"):
                    trace.texttemplate = "%{y} — %{x:d}"
                    trace.textposition = "inside"
                    trace.insidetextanchor = "start"
                    trace.constraintext = "none"
        fix_traces(fig.data)
        for frame in fig.frames:
            fix_traces(frame.data)

        # Add a time marker trace — a large text label showing the current GP/year
        # This is the most reliable way to show animated text in Plotly
        max_val = plot_data["Value"].max()
        # Add invisible scatter with text to initial data
        fig.add_trace(go.Scatter(
            x=[max_val * 0.85], y=[0.5],
            mode="text", text=["Start"],
            textfont=dict(size=36, color="rgba(0,0,0,0.15)"),
            textposition="middle center",
            showlegend=False, xaxis="x", yaxis="y",
        ))
        time_trace_idx = len(fig.data) - 1
        # Update each frame to include this trace with the current GP name (strip numeric prefix)
        for frame in fig.frames:
            raw_name = frame.name if frame.name else ""
            # Strip "0000 " prefix to show just "JPN 1990" or "Start"
            gp_display = raw_name.split(" ", 1)[1] if " " in raw_name and raw_name[:4].isdigit() else raw_name
            time_trace = go.Scatter(
                x=[max_val * 0.85], y=[0.5],
                mode="text", text=[gp_display],
                textfont=dict(size=36, color="rgba(0,0,0,0.15)"),
                textposition="middle center",
                showlegend=False,
            )
            frame.data = tuple(list(frame.data) + [time_trace])
            # Tell Plotly which traces to animate
            if not frame.traces:
                frame.traces = tuple(range(len(frame.data)))

        # Style play/pause buttons for visibility
        if fig.layout.updatemenus:
            for menu in fig.layout.updatemenus:
                menu.bgcolor = "#e0e0e0"
                menu.font = dict(color="#1a1a1a", size=13)
                menu.bordercolor = "#999999"
                menu.borderwidth = 1
        st.plotly_chart(fig, width="stretch")

    # --- Championship Bump Chart ---
    elif cross == t("cross_bump_chart"):
        st.subheader(t("bump_chart_subheader"))
        st.caption(t("bump_chart_caption"))
        bump_yr = st.selectbox(t("season"), year_list, key="bump_yr")

        bump = premier_q("""
            SELECT e.short_name, e.date_end, r.full_name AS rider,
                SUM(c.points) AS pts
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE e.season_year = ? AND s.session_type IN ('RAC','SPR')
            GROUP BY e.short_name, e.date_end, r.full_name
            ORDER BY e.date_end
        """, [bump_yr])

        if bump.empty:
            st.info(t("no_data")); st.stop()

        events_order = bump.drop_duplicates("short_name").sort_values("date_end")["short_name"].tolist()
        event_map = {e: i for i, e in enumerate(events_order)}
        pivot = bump.pivot_table(index="rider", columns="short_name", values="pts",
                                  aggfunc="sum", fill_value=0)
        # Reorder columns chronologically
        pivot = pivot[[e for e in events_order if e in pivot.columns]]
        cum = pivot.cumsum(axis=1)
        # Rank at each event (1 = most points)
        ranks = cum.rank(ascending=False, method="min").astype(int)

        # Show top N riders
        n_show = st.slider(t("show_top_n"), 5, 22, 10, key="bump_n")
        final_top = cum.iloc[:, -1].nlargest(n_show).index.tolist()
        ranks_top = ranks.loc[final_top]

        # Build long-form for plotting
        ranks_long = ranks_top.T.reset_index()
        ranks_long.columns = ["GP"] + list(ranks_top.index)
        ranks_long = ranks_long.melt(id_vars="GP", var_name="Rider", value_name="Position")

        fig = px.line(ranks_long, x="GP", y="Position", color="Rider",
                      markers=True,
                      title=t("bump_chart_title", year=bump_yr),
                      category_orders={"GP": events_order},
                      labels={"GP": t("grand_prix_label"), "Position": t("championship_position_label")})
        # Make lines thicker, markers larger for bump chart aesthetics
        fig.update_traces(line=dict(width=3), marker=dict(size=8))
        max_pos = int(ranks_long["Position"].max())
        fig.update_layout(
            height=max(500, n_show * 35),
            yaxis=dict(autorange=False, dtick=1, range=[max_pos + 0.5, 0.5], tick0=1),
            xaxis_tickangle=-45, hovermode="x unified",
        )
        st.plotly_chart(fig, width="stretch")

        # Final standings table
        final = cum.iloc[:, -1].sort_values(ascending=False).reset_index()
        final.columns = ["Rider", "Points"]
        final.insert(0, "Pos", range(1, len(final) + 1))
        final["Points"] = final["Points"].astype(int)
        st.dataframe(final.head(n_show), width="stretch", hide_index=True)

    # --- Championship Concentration: % of max possible points ---
    elif cross == t("cross_championship_concentration"):
        st.subheader(t("championship_concentration"))
        st.caption(t("championship_concentration_caption"))

        conc = premier_q("""
            SELECT e.season_year, r.full_name AS rider, SUM(c.points) AS pts,
                COUNT(CASE WHEN s.session_type = 'RAC' THEN 1 END) AS races,
                COUNT(CASE WHEN s.session_type = 'SPR' THEN 1 END) AS sprints
            FROM classifications c JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE s.session_type IN ('RAC','SPR')
            GROUP BY e.season_year, r.full_name
            ORDER BY e.season_year, pts DESC
        """)
        if conc.empty:
            st.info(t("no_data")); st.stop()

        conc["max_pts"] = conc["races"] * 25 + conc["sprints"] * 12

        rows = []
        for yr, grp in conc.groupby("season_year"):
            top3 = grp.nlargest(3, "pts")
            top3_names = ", ".join(top3["rider"].tolist())
            champion = top3.iloc[0]
            champ_pct = round(champion["pts"] / champion["max_pts"] * 100, 1) if champion["max_pts"] > 0 else 0
            top3_avg_pct = round(
                (top3["pts"] / top3["max_pts"]).mean() * 100, 1
            ) if (top3["max_pts"] > 0).all() else 0
            rows.append({
                "Year": str(int(yr)),
                "Champion": champion["rider"],
                "Champion Pts": int(champion["pts"]),
                "Champion Max": int(champion["max_pts"]),
                "Champion %": champ_pct,
                "Top 3 Avg %": top3_avg_pct,
                "Top 3": top3_names,
            })
        df = pd.DataFrame(rows)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["Year"], y=df["Top 3 Avg %"], name=t("top3_avg_efficiency"),
                             marker_color="#3498db", text=df["Top 3 Avg %"].astype(str) + "%",
                             textposition="outside"))
        fig.add_trace(go.Scatter(x=df["Year"], y=df["Champion %"], name=t("champion_efficiency"),
                                 mode="lines+markers", marker=dict(size=10, color="#e74c3c"),
                                 line=dict(width=3)))
        max_val = max(df["Top 3 Avg %"].max(), df["Champion %"].max())
        fig.update_layout(height=450, title=t("points_efficiency_title"),
                          yaxis_title=t("pct_max_possible_points"), hovermode="x unified",
                          yaxis=dict(range=[0, max_val * 1.15]))
        st.plotly_chart(fig, width="stretch")

        st.dataframe(df, width="stretch", hide_index=True)

    # --- Top Riders Evolution ---
    elif cross == t("cross_top_riders"):
        st.subheader(t("top_riders_evolution"))
        st.caption(t("top_riders_evolution_caption"))

        rider_yr = premier_q("""
            SELECT e.season_year, r.full_name AS rider,
                SUM(CASE WHEN s.session_type = 'RAC' THEN c.points ELSE 0 END) AS race_pts,
                SUM(c.points) AS total_pts,
                COUNT(CASE WHEN s.session_type = 'RAC' AND c.position = 1 THEN 1 END) AS wins,
                COUNT(CASE WHEN s.session_type = 'RAC' AND c.position <= 3 THEN 1 END) AS podiums,
                COUNT(CASE WHEN s.session_type = 'RAC' THEN 1 END) AS races,
                COUNT(CASE WHEN s.session_type = 'SPR' THEN 1 END) AS sprints
            FROM classifications c JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE s.session_type IN ('RAC','SPR')
            GROUP BY e.season_year, r.full_name
        """)
        if rider_yr.empty:
            st.info(t("no_data")); st.stop()

        # Max possible points
        rider_yr["max_pts"] = rider_yr["races"] * 25 + rider_yr["sprints"] * 12
        rider_yr["pts_pct"] = (rider_yr["total_pts"] / rider_yr["max_pts"] * 100).round(1)
        rider_yr["Year"] = rider_yr["season_year"].astype(str)

        # Pick top riders by total career wins
        career_wins = rider_yr.groupby("rider")["wins"].sum().nlargest(10).index.tolist()
        top = rider_yr[rider_yr["rider"].isin(career_wins)]

        # Wins per year
        fig = px.line(top, x="Year", y="wins", color="rider", markers=True,
                      title=t("race_wins_per_season"), labels={"wins": t("wins")})
        fig.update_layout(height=420, hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

        # Points % per year
        fig2 = px.line(top, x="Year", y="pts_pct", color="rider", markers=True,
                       title=t("points_efficiency_pct_title"),
                       labels={"pts_pct": t("points_pct")})
        fig2.update_layout(height=420, hovermode="x unified")
        st.plotly_chart(fig2, width="stretch")

        # Podiums per year
        fig3 = px.line(top, x="Year", y="podiums", color="rider", markers=True,
                       title=t("podiums_per_season"), labels={"podiums": t("podiums")})
        fig3.update_layout(height=420, hovermode="x unified")
        st.plotly_chart(fig3, width="stretch")

        # Summary table
        st.subheader(t("career_totals"))
        career = rider_yr[rider_yr["rider"].isin(career_wins)].groupby("rider").agg(
            Seasons=("season_year", "nunique"), Races=("races", "sum"),
            Wins=("wins", "sum"), Podiums=("podiums", "sum"),
            Points=("total_pts", "sum"), Max_Pts=("max_pts", "sum"),
        ).reset_index()
        career["Pts %"] = (career["Points"] / career["Max_Pts"] * 100).round(1)
        career["Points"] = career["Points"].astype(int)
        career = career.sort_values("Wins", ascending=False)
        career = career.drop("Max_Pts", axis=1)
        career.columns = ["Rider", "Seasons", "Races", "Wins", "Podiums", "Points", "Pts %"]
        st.dataframe(career, width="stretch", hide_index=True)

    # --- Team Evolution ---
    elif cross == t("cross_team_evolution"):
        st.subheader(t("team_evolution"))
        st.caption(t("team_evolution_caption"))

        teams = premier_q("""
            SELECT e.season_year, COALESCE(ta.canonical_name, t.team_name) AS Team,
                SUM(c.points) AS total_pts,
                COUNT(CASE WHEN c.position = 1 AND s.session_type = 'RAC' THEN 1 END) AS wins,
                COUNT(CASE WHEN c.position <= 3 AND s.session_type = 'RAC' THEN 1 END) AS podiums,
                COUNT(DISTINCT r.rider_id) AS riders
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
            LEFT JOIN team_aliases ta ON t.team_name = ta.team_name
            WHERE s.session_type IN ('RAC','SPR') AND t.team_name IS NOT NULL
            GROUP BY e.season_year, COALESCE(ta.canonical_name, t.team_name)
        """)
        if teams.empty:
            st.info(t("no_data")); st.stop()

        teams["Year"] = teams["season_year"].astype(str)

        # Top teams by career points
        career_pts = teams.groupby("Team")["total_pts"].sum().nlargest(10).index.tolist()
        top = teams[teams["Team"].isin(career_pts)]

        fig = px.line(top, x="Year", y="total_pts", color="Team", markers=True,
                      title=t("team_total_pts_title"),
                      labels={"total_pts": t("points")})
        fig.update_layout(height=450, hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

        # Team wins stacked
        team_wins = top[top["wins"] > 0]
        if not team_wins.empty:
            fig2 = px.bar(team_wins, x="Year", y="wins", color="Team", barmode="stack",
                          title=t("race_wins_by_team"), labels={"wins": t("wins")})
            fig2.update_layout(height=420)
            st.plotly_chart(fig2, width="stretch")

        # Team podiums
        fig3 = px.line(top, x="Year", y="podiums", color="Team", markers=True,
                       title=t("podiums_by_team"), labels={"podiums": t("podiums")})
        fig3.update_layout(height=420, hovermode="x unified")
        st.plotly_chart(fig3, width="stretch")

        # Team standings table per year
        st.subheader(t("alltime_team_rankings"))
        team_career = teams.groupby("Team").agg(
            Seasons=("season_year", "nunique"), Points=("total_pts", "sum"),
            Wins=("wins", "sum"), Podiums=("podiums", "sum"),
        ).reset_index().sort_values("Points", ascending=False)
        team_career["Points"] = team_career["Points"].astype(int)
        st.dataframe(team_career.head(15), width="stretch", hide_index=True)

    # --- Constructor Evolution ---
    elif cross == t("cross_constructor_evolution"):
        st.subheader(t("constructor_evolution"))

        const = premier_q("""
            SELECT e.season_year, t.constructor,
                COUNT(DISTINCT r.rider_id) AS riders,
                SUM(c.points) AS total_pts,
                COUNT(CASE WHEN c.position = 1 AND s.session_type = 'RAC' THEN 1 END) AS wins,
                COUNT(CASE WHEN s.session_type = 'RAC' THEN 1 END) AS race_entries
            FROM classifications c JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
            WHERE s.session_type IN ('RAC','SPR') AND t.constructor IS NOT NULL
            GROUP BY e.season_year, t.constructor
        """)
        if const.empty:
            st.info(t("no_data")); st.stop()

        const["Year"] = const["season_year"].astype(str)
        const["avg_pts"] = (const["total_pts"] / const["riders"]).round(1)

        # Avg points per rider (fair comparison)
        fig = px.line(const, x="Year", y="avg_pts", color="constructor", markers=True,
                      title=t("constructor_avg_pts_title"),
                      labels={"avg_pts": t("avg_pts_rider_label"), "constructor": t("constructor")})
        fig.update_layout(height=420, hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

        # Win share per season (stacked area)
        const_wins = const[const["wins"] > 0].copy()
        fig2 = px.bar(const_wins, x="Year", y="wins", color="constructor", barmode="stack",
                      title=t("race_wins_by_constructor"),
                      labels={"wins": t("wins")})
        fig2.update_layout(height=420)
        st.plotly_chart(fig2, width="stretch")

        # Number of riders per constructor
        fig3 = px.bar(const, x="Year", y="riders", color="constructor", barmode="group",
                      title=t("grid_size_constructor"),
                      labels={"riders": t("riders")})
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, width="stretch")

    # --- Rider Career Tracker ---
    elif cross == t("cross_rider_career"):
        st.subheader(t("rider_career_tracker"))
        st.caption(t("rider_career_caption"))

        all_riders = premier_q("""
            SELECT r.full_name, COUNT(DISTINCT e.season_year) AS seasons,
                SUM(CASE WHEN s.session_type = 'RAC' AND c.position = 1 THEN 1 ELSE 0 END) AS wins
            FROM classifications c JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE s.session_type IN ('RAC','SPR')
            GROUP BY r.full_name HAVING COUNT(DISTINCT e.season_year) >= 2
            ORDER BY wins DESC
        """)
        if all_riders.empty:
            st.info(t("no_data")); st.stop()

        default_riders = all_riders["full_name"].head(5).tolist()
        sel_riders = st.multiselect(t("riders_to_compare"), all_riders["full_name"].tolist(),
                                    default=default_riders, key="career_riders")
        if not sel_riders:
            st.info(t("select_rider")); st.stop()

        ph = ",".join("?" * len(sel_riders))
        rd = premier_q(f"""
            SELECT e.season_year, r.full_name AS rider,
                SUM(c.points) AS pts,
                COUNT(CASE WHEN s.session_type = 'RAC' AND c.position = 1 THEN 1 END) AS wins,
                COUNT(CASE WHEN s.session_type = 'RAC' AND c.position <= 3 THEN 1 END) AS podiums,
                COUNT(CASE WHEN s.session_type = 'RAC' THEN 1 END) AS races,
                COUNT(CASE WHEN s.session_type = 'SPR' THEN 1 END) AS sprints,
                COUNT(CASE WHEN s.session_type = 'Q' AND s.session_number = 2 AND c.position = 1 THEN 1 END) AS poles
            FROM classifications c JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE r.full_name IN ({ph}) AND s.session_type IN ('RAC','SPR','Q')
            GROUP BY e.season_year, r.full_name
            ORDER BY e.season_year
        """, sel_riders)

        if rd.empty:
            st.info(t("no_data")); st.stop()

        rd["Year"] = rd["season_year"].astype(str)
        rd["max_pts"] = rd["races"] * 25 + rd["sprints"] * 12
        rd["pts_pct"] = (rd["pts"] / rd["max_pts"] * 100).round(1)
        rd["win_pct"] = (rd["wins"] / rd["races"].replace(0, 1) * 100).round(1)

        metric = st.selectbox(t("metric_label"), [
            t("points"), t("points_pct"), t("wins"), t("ranking_win_rate"), t("podiums"), t("poles")
        ], key="career_metric")

        metric_map = {t("points"): "pts", t("points_pct"): "pts_pct", t("wins"): "wins",
                      t("ranking_win_rate"): "win_pct", t("podiums"): "podiums", t("poles"): "poles"}
        col = metric_map[metric]

        fig = px.line(rd, x="Year", y=col, color="rider", markers=True,
                      title=t("metric_per_season", metric=metric),
                      labels={col: metric})
        fig.update_layout(height=450, hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

        # Cumulative career metrics
        st.subheader(t("cumulative_career_comparison"))
        for r_name in sel_riders:
            rd_r = rd[rd["rider"] == r_name].sort_values("season_year")
            rd.loc[rd["rider"] == r_name, "cum_wins"] = rd_r["wins"].cumsum().values
            rd.loc[rd["rider"] == r_name, "cum_pts"] = rd_r["pts"].cumsum().values
            rd.loc[rd["rider"] == r_name, "cum_podiums"] = rd_r["podiums"].cumsum().values

        cum_metric = st.selectbox(t("cumulative_metric_label"), [t("wins"), t("points"), t("podiums")], key="cum_m")
        cum_col = {t("wins"): "cum_wins", t("points"): "cum_pts", t("podiums"): "cum_podiums"}[cum_metric]

        fig2 = px.line(rd, x="Year", y=cum_col, color="rider", markers=True,
                       title=t("cumulative_title", metric=cum_metric),
                       labels={cum_col: t("total_metric", metric=cum_metric)})
        fig2.update_layout(height=420, hovermode="x unified")
        st.plotly_chart(fig2, width="stretch")

    # --- Qualifying vs Race ---
    elif cross == t("cross_qualifying_race"):
        st.subheader(t("qualifying_vs_race"))
        st.caption(t("qualifying_vs_race_caption"))

        qvr = premier_q("""
            SELECT e.season_year, e.short_name, r.full_name AS rider,
                grid.grid_pos, race.finish_pos
            FROM (
                SELECT e2.event_id, c2.rider_id, c2.position AS grid_pos
                FROM classifications c2
                JOIN sessions s2 ON c2.session_id = s2.session_id
                JOIN events e2 ON s2.event_id = e2.event_id
                WHERE s2.session_type = 'Q' AND s2.session_number = 2 AND c2.position IS NOT NULL
            ) grid
            JOIN (
                SELECT e3.event_id, c3.rider_id, c3.position AS finish_pos
                FROM classifications c3
                JOIN sessions s3 ON c3.session_id = s3.session_id
                JOIN events e3 ON s3.event_id = e3.event_id
                WHERE s3.session_type = 'RAC' AND c3.position IS NOT NULL
            ) race ON grid.event_id = race.event_id AND grid.rider_id = race.rider_id
            JOIN events e ON e.event_id = grid.event_id
            JOIN riders r ON r.rider_id = grid.rider_id
        """)

        if qvr.empty:
            st.info(t("no_data")); st.stop()

        qvr["Year"] = qvr["season_year"].astype(str)
        qvr["positions_gained"] = qvr["grid_pos"] - qvr["finish_pos"]  # positive = gained

        # Average positions gained per rider across all races
        avg_gain = qvr.groupby("rider").agg(
            avg_gained=("positions_gained", "mean"),
            races=("short_name", "nunique"),
        ).reset_index()
        avg_gain = avg_gain[avg_gain["races"] >= 5]
        avg_gain["avg_gained"] = avg_gain["avg_gained"].round(2)

        # Best gainers
        gainers = avg_gain.sort_values("avg_gained", ascending=False).head(15)
        fig = px.bar(gainers, x="rider", y="avg_gained", text="avg_gained",
                     title=t("best_race_starters_title"),
                     color="avg_gained", color_continuous_scale="RdYlGn",
                     labels={"avg_gained": t("avg_positions_gained"), "rider": ""})
        fig.update_layout(height=450, xaxis_tickangle=-45, coloraxis_showscale=False,
                          yaxis=dict(range=[min(0, gainers["avg_gained"].min() - 0.5),
                                            gainers["avg_gained"].max() * 1.2]))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, width="stretch")

        # Trend: avg positions gained per year (top riders)
        st.subheader(t("positions_gained_trend"))
        top_riders = avg_gain.nlargest(8, "avg_gained")["rider"].tolist()
        yr_gain = qvr[qvr["rider"].isin(top_riders)].groupby(["Year", "rider"])["positions_gained"].mean().round(2).reset_index()
        fig2 = px.line(yr_gain, x="Year", y="positions_gained", color="rider", markers=True,
                       title=t("avg_gained_per_season_title"),
                       labels={"positions_gained": t("avg_gained_label")})
        fig2.update_layout(height=420, hovermode="x unified")
        st.plotly_chart(fig2, width="stretch")

        # Scatter: grid pos vs finish pos for all data
        st.subheader(t("grid_vs_finish"))
        fig3 = px.density_heatmap(qvr, x="grid_pos", y="finish_pos",
                                   title=t("grid_vs_finish_density_title"),
                                   labels={"grid_pos": t("grid_position"), "finish_pos": t("finish_position")},
                                   nbinsx=22, nbinsy=22, color_continuous_scale="YlOrRd")
        fig3.update_layout(height=500,
                           yaxis=dict(autorange="reversed"),
                           xaxis=dict(dtick=1), yaxis_dtick=1)
        st.plotly_chart(fig3, width="stretch")

    # --- DNF & Safety Trends ---
    elif cross == t("cross_dnf_safety"):
        st.subheader(t("dnf_safety_trends"))
        st.caption(t("dnf_safety_caption"))

        dnf = premier_q("""
            SELECT e.season_year, cl.status, COUNT(*) AS cnt
            FROM classifications cl
            JOIN sessions s ON cl.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            WHERE s.session_type = 'RAC'
            GROUP BY e.season_year, cl.status
        """)
        if dnf.empty:
            st.info(t("no_data")); st.stop()

        STATUS_MAP = {"INSTND": "Finished", "OUTSTND": "DNF",
                      "NOTFINISHFIRST": "DNF Lap 1", "NOTSTARTED": "DNS"}
        dnf["outcome"] = dnf["status"].map(STATUS_MAP).fillna("Other")
        dnf["Year"] = dnf["season_year"].astype(str)

        # Totals per year
        yr_totals = dnf.groupby(["Year", "outcome"])["cnt"].sum().reset_index()
        yr_sum = yr_totals.groupby("Year")["cnt"].sum().reset_index().rename(columns={"cnt": "total"})

        # DNF rate per year
        dnf_rate = yr_totals[yr_totals["outcome"] != "Finished"].groupby("Year")["cnt"].sum().reset_index()
        dnf_rate = dnf_rate.merge(yr_sum, on="Year")
        dnf_rate["dnf_pct"] = (dnf_rate["cnt"] / dnf_rate["total"] * 100).round(1)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=dnf_rate["Year"], y=dnf_rate["dnf_pct"],
                             name="DNF Rate %", marker_color="#e74c3c",
                             text=dnf_rate["dnf_pct"].astype(str) + "%", textposition="outside"))
        fig.update_layout(height=400, title=t("dnf_rate_title"),
                          yaxis_title=t("dnf_rate_yaxis"))
        st.plotly_chart(fig, width="stretch")

        # Avg DNFs per race
        races_per_yr = premier_q("""
            SELECT e.season_year, COUNT(DISTINCT s.session_id) AS n_races
            FROM sessions s JOIN events e ON s.event_id = e.event_id
            WHERE s.session_type = 'RAC' GROUP BY e.season_year
        """)
        dnf_counts = yr_totals[yr_totals["outcome"].isin(["DNF", "DNF Lap 1"])].groupby("Year")["cnt"].sum().reset_index()
        dnf_counts["Year_int"] = dnf_counts["Year"].astype(int)
        races_per_yr["Year"] = races_per_yr["season_year"].astype(str)
        avg_dnf = dnf_counts.merge(races_per_yr, on="Year")
        avg_dnf["avg_dnf_per_race"] = (avg_dnf["cnt"] / avg_dnf["n_races"]).round(2)

        fig2 = px.line(avg_dnf, x="Year", y="avg_dnf_per_race", markers=True,
                       title=t("avg_dnf_per_race_title"),
                       labels={"avg_dnf_per_race": t("avg_dnf_per_race_label")})
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, width="stretch")

        # Breakdown stacked bar
        fig3 = px.bar(yr_totals, x="Year", y="cnt", color="outcome", barmode="stack",
                      title=t("race_outcomes_per_season"),
                      labels={"cnt": t("riders")},
                      color_discrete_map={"Finished": "#2ecc71", "DNF": "#e74c3c",
                                          "DNF Lap 1": "#e67e22", "DNS": "#95a5a6"})
        fig3.update_layout(height=420)
        st.plotly_chart(fig3, width="stretch")

    # --- Pole Position Stats ---
    elif cross == t("cross_pole_stats"):
        st.subheader(t("pole_position_trends"))
        st.caption(t("pole_caption"))

        poles = premier_q("""
            SELECT e.season_year, r.full_name AS rider, t.constructor,
                COUNT(*) AS poles
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year
            WHERE s.session_type = 'Q' AND c.position = 1
                AND s.session_number = 2
            GROUP BY e.season_year, r.full_name, t.constructor
        """)
        if poles.empty:
            st.info(t("no_qualifying_data")); st.stop()

        poles["Year"] = poles["season_year"].astype(str)

        # Poles per rider per year (top riders)
        career_poles = poles.groupby("rider")["poles"].sum().nlargest(8).index.tolist()
        top_poles = poles[poles["rider"].isin(career_poles)]

        fig = px.line(top_poles, x="Year", y="poles", color="rider", markers=True,
                      title=t("poles_per_season_title"),
                      labels={"poles": t("poles")})
        fig.update_layout(height=420, hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

        # Poles by constructor
        const_poles = poles.groupby(["Year", "constructor"])["poles"].sum().reset_index()
        fig2 = px.bar(const_poles, x="Year", y="poles", color="constructor", barmode="stack",
                      title=t("poles_by_constructor_title"),
                      labels={"poles": t("poles")})
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, width="stretch")

        # Career pole table
        st.subheader(t("alltime_poles"))
        all_poles = poles.groupby("rider")["poles"].sum().sort_values(ascending=False).reset_index()
        all_poles.columns = ["Rider", "Poles"]
        st.dataframe(all_poles.head(15), width="stretch", hide_index=True)

    # --- Race Competitiveness ---
    elif cross == t("cross_race_competitiveness"):
        st.subheader(t("race_competitiveness"))
        st.caption(t("race_competitiveness_caption"))

        comp = premier_q("""
            SELECT e.season_year, e.short_name, r.full_name AS rider,
                c.position, c.gap_first
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE s.session_type = 'RAC' AND c.position <= 5
        """)
        if comp.empty:
            st.info(t("no_data")); st.stop()

        # Parse gap_first to float
        comp["gap_sec"] = comp["gap_first"].apply(lap_to_sec)

        rows = []
        for yr, grp in comp.groupby("season_year"):
            winners = grp[grp["position"] == 1]["rider"].nunique()
            gap_2nd = grp[grp["position"] == 2]["gap_sec"].dropna().mean()
            gap_3rd = grp[grp["position"] == 3]["gap_sec"].dropna().mean()
            gap_5th = grp[grp["position"] == 5]["gap_sec"].dropna().mean()
            races = grp[grp["position"] == 1].shape[0]
            rows.append({
                "Year": str(int(yr)), "Races": races,
                "Different Winners": winners,
                "Avg Gap to P2 (s)": round(gap_2nd, 2) if gap_2nd else None,
                "Avg Gap to P3 (s)": round(gap_3rd, 2) if gap_3rd else None,
                "Avg Gap to P5 (s)": round(gap_5th, 2) if gap_5th else None,
            })
        cdf = pd.DataFrame(rows)

        # Different winners per season
        fig = px.bar(cdf, x="Year", y="Different Winners", text="Different Winners",
                     title=t("different_winners_per_season"),
                     color="Different Winners", color_continuous_scale="Viridis")
        fig.update_layout(height=380, coloraxis_showscale=False)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, width="stretch")

        # Average gaps trend
        gap_melt = cdf.melt(id_vars="Year",
                            value_vars=["Avg Gap to P2 (s)", "Avg Gap to P3 (s)", "Avg Gap to P5 (s)"],
                            var_name="Gap to", value_name="Seconds")
        fig2 = px.line(gap_melt, x="Year", y="Seconds", color="Gap to", markers=True,
                       title=t("avg_winner_gap_title"),
                       labels={"Seconds": t("avg_gap_s")})
        fig2.update_layout(height=400, hovermode="x unified")
        st.plotly_chart(fig2, width="stretch")

        st.dataframe(cdf, width="stretch", hide_index=True)

    # --- Season Dominance Index ---
    elif cross == t("cross_season_dominance"):
        st.subheader(t("season_dominance_index"))
        st.caption(t("season_dominance_caption"))

        champ = premier_q("""
            SELECT e.season_year, r.full_name AS rider,
                SUM(c.points) AS pts,
                COUNT(CASE WHEN c.position = 1 THEN 1 END) AS wins,
                COUNT(CASE WHEN c.position <= 3 THEN 1 END) AS podiums,
                COUNT(*) AS races
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE s.session_type = 'RAC'
            GROUP BY e.season_year, r.full_name
        """)
        if champ.empty:
            st.info(t("no_data")); st.stop()

        rows = []
        for yr, grp in champ.groupby("season_year"):
            top2 = grp.nlargest(2, "pts")
            if len(top2) < 2:
                continue
            p1, p2 = top2.iloc[0], top2.iloc[1]
            rows.append({
                "Year": str(int(yr)),
                "Champion": p1["rider"],
                "Points": int(p1["pts"]),
                "Runner-up": p2["rider"],
                "Runner-up Pts": int(p2["pts"]),
                "Margin": int(p1["pts"] - p2["pts"]),
                "Wins": int(p1["wins"]),
                "Win Rate %": round(p1["wins"] / p1["races"] * 100, 1),
                "Podium Rate %": round(p1["podiums"] / p1["races"] * 100, 1),
                "Races": int(p1["races"]),
            })
        dom = pd.DataFrame(rows)

        # Margin over runner-up
        fig = px.bar(dom, x="Year", y="Margin", text="Champion",
                     title=t("champion_margin_title"),
                     color="Margin", color_continuous_scale="RdYlGn")
        fig.update_layout(height=420, coloraxis_showscale=False)
        fig.update_traces(textposition="outside", textfont_size=10)
        st.plotly_chart(fig, width="stretch")

        # Win rate + podium rate
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=dom["Year"], y=dom["Win Rate %"], name=t("ranking_win_rate"),
                              marker_color="#FFD700", text=dom["Win Rate %"].astype(str) + "%",
                              textposition="outside"))
        fig2.add_trace(go.Bar(x=dom["Year"], y=dom["Podium Rate %"], name=t("ranking_podium_rate"),
                              marker_color="#C0C0C0", text=dom["Podium Rate %"].astype(str) + "%",
                              textposition="outside"))
        fig2.update_layout(height=420, title=t("champion_rates_title"),
                           barmode="group", yaxis_title="%")
        st.plotly_chart(fig2, width="stretch")

        st.dataframe(dom, width="stretch", hide_index=True)

    # --- Nationality Trends ---
    elif cross == t("cross_nationality_trends"):
        st.subheader(t("nationality_trends"))
        st.caption(t("nationality_trends_caption"))

        nat = premier_q("""
            SELECT e.season_year, r.nationality AS country,
                COUNT(DISTINCT r.rider_id) AS riders,
                SUM(c.points) AS pts,
                COUNT(CASE WHEN c.position = 1 THEN 1 END) AS wins
            FROM classifications c
            JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE s.session_type = 'RAC' AND r.nationality IS NOT NULL
            GROUP BY e.season_year, r.nationality
        """)
        if nat.empty:
            st.info(t("no_data")); st.stop()

        nat["Year"] = nat["season_year"].astype(str)

        # Points by nationality stacked
        top_nations = nat.groupby("country")["pts"].sum().nlargest(8).index.tolist()
        nat_top = nat[nat["country"].isin(top_nations)]

        fig = px.bar(nat_top, x="Year", y="pts", color="country", barmode="stack",
                     title=t("race_pts_by_nationality"),
                     labels={"pts": t("points"), "country": t("nationality")})
        fig.update_layout(height=450)
        st.plotly_chart(fig, width="stretch")

        # Wins by nationality
        nat_wins = nat_top[nat_top["wins"] > 0]
        if not nat_wins.empty:
            fig2 = px.bar(nat_wins, x="Year", y="wins", color="country", barmode="stack",
                          title=t("race_wins_by_nationality"),
                          labels={"wins": t("wins")})
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, width="stretch")

        # Grid diversity — unique nationalities per season
        diversity = nat.groupby("Year")["country"].nunique().reset_index()
        diversity.columns = ["Year", "Nationalities"]
        fig3 = px.line(diversity, x="Year", y="Nationalities", markers=True,
                       title=t("grid_nationality_diversity"),
                       labels={"Nationalities": t("unique_nationalities")})
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, width="stretch")

    # --- Circuit Pace Evolution ---
    elif cross == t("cross_circuit_pace"):
        st.subheader(t("circuit_pace_evolution"))
        st.caption(t("circuit_pace_caption"))

        pace = premier_q("""
            SELECT e.season_year, e.short_name, r.full_name AS rider, c.best_lap_time
            FROM classifications c JOIN sessions s ON c.session_id = s.session_id
            JOIN events e ON s.event_id = e.event_id
            JOIN riders r ON c.rider_id = r.rider_id
            WHERE s.session_type = 'RAC' AND c.position = 1""")
        if not pace.empty:
            pace["sec"] = pace["best_lap_time"].apply(lap_to_sec)
            pace = pace.dropna(subset=["sec"])
            pace["season_year"] = pace["season_year"].astype(str)
            circuits = sorted(pace["short_name"].unique())
            sc = st.multiselect(t("circuits_multiselect"), circuits, default=circuits[:5], key="pc")
            if sc:
                fig = px.line(pace[pace["short_name"].isin(sc)], x="season_year", y="sec",
                              color="short_name", markers=True, text="rider",
                              title=t("winner_best_lap_by_year"),
                              labels={"season_year": t("year"), "sec": t("lap_s")})
                fig.update_traces(textposition="top center", textfont_size=9)
                fig.update_layout(height=500)
                st.plotly_chart(fig, width="stretch")
