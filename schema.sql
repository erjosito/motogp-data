-- MotoGP Data Platform — SQL Schema
-- Azure SQL Serverless (motogpdb)

-- Riders dimension
CREATE TABLE riders (
    rider_id        NVARCHAR(50)  NOT NULL PRIMARY KEY,  -- API UUID
    full_name       NVARCHAR(100) NOT NULL,
    number          INT           NULL,
    nationality_iso NVARCHAR(5)   NULL,
    nationality     NVARCHAR(60)  NULL
);

-- Teams dimension (changes per season)
CREATE TABLE teams (
    team_id         NVARCHAR(50)  NOT NULL,
    season_year     INT           NOT NULL,
    team_name       NVARCHAR(120) NOT NULL,
    constructor     NVARCHAR(60)  NULL,
    constructor_id  NVARCHAR(50)  NULL,
    PRIMARY KEY (team_id, season_year)
);

-- Events (GP weekends)
CREATE TABLE events (
    event_id        NVARCHAR(50)  NOT NULL PRIMARY KEY,
    season_year     INT           NOT NULL,
    short_name      NVARCHAR(10)  NOT NULL,   -- THA, BRA, USA, etc.
    event_name      NVARCHAR(200) NOT NULL,
    sponsored_name  NVARCHAR(200) NULL,
    circuit_name    NVARCHAR(200) NULL,
    circuit_place   NVARCHAR(100) NULL,
    country_name    NVARCHAR(100) NULL,
    country_iso     NVARCHAR(5)   NULL,
    date_start      DATE          NULL,
    date_end        DATE          NULL
);
CREATE INDEX IX_events_season ON events (season_year);

-- Sessions (FP1, PR, FP2, Q1, Q2, SPR, WUP, RAC per event)
CREATE TABLE sessions (
    session_id      NVARCHAR(50)  NOT NULL PRIMARY KEY,
    event_id        NVARCHAR(50)  NOT NULL REFERENCES events(event_id),
    category        NVARCHAR(20)  NOT NULL,   -- MotoGP, Moto2, Moto3
    session_type    NVARCHAR(10)  NOT NULL,   -- FP, PR, Q, SPR, WUP, RAC
    session_number  INT           NULL,        -- 1, 2 for FP1/FP2, Q1/Q2
    session_label   NVARCHAR(30)  NOT NULL,   -- "Free Practice 1", "Race", etc.
    session_date    DATETIME2     NULL,
    track_condition NVARCHAR(20)  NULL,
    weather         NVARCHAR(30)  NULL,
    air_temp        NVARCHAR(10)  NULL,
    ground_temp     NVARCHAR(10)  NULL,
    humidity        NVARCHAR(10)  NULL,
    status          NVARCHAR(20)  NULL
);
CREATE INDEX IX_sessions_event ON sessions (event_id);

-- Classifications (per-session results from API)
CREATE TABLE classifications (
    session_id      NVARCHAR(50)  NOT NULL REFERENCES sessions(session_id),
    rider_id        NVARCHAR(50)  NOT NULL REFERENCES riders(rider_id),
    position        INT           NULL,
    team_id         NVARCHAR(50)  NULL,
    total_laps      INT           NULL,
    time_ms         BIGINT        NULL,       -- total time in ms (race sessions)
    time_text       NVARCHAR(30)  NULL,       -- formatted time string
    gap_first       NVARCHAR(20)  NULL,
    gap_prev        NVARCHAR(20)  NULL,
    best_lap_number INT           NULL,
    best_lap_time   NVARCHAR(20)  NULL,
    top_speed       FLOAT         NULL,
    points          FLOAT         NULL,
    status          NVARCHAR(20)  NULL,       -- INSTND, DNF, etc.
    PRIMARY KEY (session_id, rider_id)
);

-- Lap-by-lap data (parsed from official timing PDFs)
CREATE TABLE laps (
    session_id      NVARCHAR(50)  NOT NULL REFERENCES sessions(session_id),
    rider_id        NVARCHAR(50)  NOT NULL REFERENCES riders(rider_id),
    lap_number      INT           NOT NULL,
    lap_time        NVARCHAR(20)  NULL,       -- m:ss.mmm format
    t1              NVARCHAR(20)  NULL,       -- sector 1 time
    t2              NVARCHAR(20)  NULL,       -- sector 2 time
    t3              NVARCHAR(20)  NULL,       -- sector 3 time
    t4              NVARCHAR(20)  NULL,       -- sector 4 time
    speed_kmh       FLOAT         NULL,
    is_pit          BIT           NOT NULL DEFAULT 0,
    run_number      INT           NULL,       -- stint number
    front_tyre      NVARCHAR(30)  NULL,       -- e.g. Slick-Medium
    rear_tyre       NVARCHAR(30)  NULL,
    PRIMARY KEY (session_id, rider_id, lap_number)
);
CREATE INDEX IX_laps_session ON laps (session_id);
CREATE INDEX IX_laps_rider ON laps (rider_id);

-- Useful views for analytics / Power BI

-- Denormalized lap view with all context
CREATE VIEW vw_laps_full AS
SELECT
    e.season_year,
    e.short_name       AS event_short,
    e.event_name,
    e.circuit_name,
    e.country_name,
    s.session_type,
    s.session_number,
    s.session_label,
    s.session_date,
    s.weather,
    r.full_name        AS rider,
    r.number           AS rider_number,
    r.nationality,
    t.team_name,
    t.constructor,
    l.lap_number,
    l.lap_time,
    l.t1, l.t2, l.t3, l.t4,
    l.speed_kmh,
    l.is_pit,
    l.run_number,
    l.front_tyre,
    l.rear_tyre
FROM laps l
JOIN sessions s ON l.session_id = s.session_id
JOIN events e   ON s.event_id = e.event_id
JOIN riders r   ON l.rider_id = r.rider_id
LEFT JOIN teams t ON t.team_id = (
    SELECT TOP 1 c.team_id FROM classifications c
    WHERE c.session_id = l.session_id AND c.rider_id = l.rider_id
) AND t.season_year = e.season_year;

-- Denormalized classification view
CREATE VIEW vw_classifications_full AS
SELECT
    e.season_year,
    e.short_name       AS event_short,
    e.event_name,
    e.circuit_name,
    s.session_type,
    s.session_number,
    s.session_label,
    s.session_date,
    c.position,
    r.full_name        AS rider,
    r.number           AS rider_number,
    r.nationality,
    t.team_name,
    t.constructor,
    c.total_laps,
    c.time_text,
    c.gap_first,
    c.best_lap_time,
    c.top_speed,
    c.points,
    c.status
FROM classifications c
JOIN sessions s ON c.session_id = s.session_id
JOIN events e   ON s.event_id = e.event_id
JOIN riders r   ON c.rider_id = r.rider_id
LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year;
