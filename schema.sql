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
    status          NVARCHAR(20)  NULL,
    source_kind     NVARCHAR(30)  NOT NULL DEFAULT 'official-api'
);
CREATE INDEX IX_sessions_event ON sessions (event_id);

-- Classifications (per-session results from API)
CREATE TABLE classifications (
    session_id      NVARCHAR(50)  NOT NULL REFERENCES sessions(session_id),
    rider_id        NVARCHAR(50)  NOT NULL REFERENCES riders(rider_id),
    position        INT           NULL,
    team_id         NVARCHAR(50)  NULL,
    total_laps      INT           NULL,
    time_ms         NVARCHAR(30)  NULL,       -- legacy raw API timing text; not normalized milliseconds
    time_text       NVARCHAR(30)  NULL,       -- formatted time string
    gap_first       NVARCHAR(20)  NULL,
    gap_prev        NVARCHAR(20)  NULL,
    best_lap_number INT           NULL,
    best_lap_time   NVARCHAR(20)  NULL,
    top_speed       FLOAT         NULL,
    points          FLOAT         NULL,
    status          NVARCHAR(20)  NULL,       -- INSTND, DNF, etc.
    constructor_id  NVARCHAR(50)  NULL,
    constructor_name NVARCHAR(60) NULL,
    rider_number    INT NULL,
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

CREATE TABLE schema_migrations (
    version         NVARCHAR(100) NOT NULL PRIMARY KEY,
    applied_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE championship_standings (
    season_year     INT NOT NULL,
    category        NVARCHAR(20) NOT NULL,
    rider_id        NVARCHAR(50) NOT NULL REFERENCES riders(rider_id),
    position        INT NOT NULL,
    points          DECIMAL(10,3) NOT NULL,
    constructor_id  NVARCHAR(50) NULL,
    constructor_name NVARCHAR(60) NULL,
    is_final        BIT NOT NULL,
    source_url      NVARCHAR(1024) NOT NULL,
    source_json     NVARCHAR(MAX) NOT NULL CHECK (ISJSON(source_json) = 1),
    fetched_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    PRIMARY KEY (season_year, category, rider_id)
);

CREATE TABLE historical_imports (
    season_year     INT NOT NULL,
    category        NVARCHAR(20) NOT NULL,
    source_hash     CHAR(64) NOT NULL,
    event_count     INT NOT NULL,
    session_count   INT NOT NULL,
    classification_count INT NOT NULL,
    standings_count INT NOT NULL,
    source_payload  NVARCHAR(MAX) NOT NULL CHECK (ISJSON(source_payload) = 1),
    imported_at     DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    PRIMARY KEY (season_year, category)
);

CREATE TABLE external_sources (
    source_id NVARCHAR(80) NOT NULL PRIMARY KEY,
    source_url NVARCHAR(1024) NOT NULL,
    declared_license NVARCHAR(100) NOT NULL,
    content_hash CHAR(64) NOT NULL,
    fetched_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE external_candidates (
    candidate_id CHAR(64) NOT NULL PRIMARY KEY,
    source_id NVARCHAR(80) NOT NULL REFERENCES external_sources(source_id),
    season_year INT NOT NULL,
    category NVARCHAR(20) NOT NULL,
    event_short NVARCHAR(10) NOT NULL,
    rider_name NVARCHAR(100) NOT NULL,
    source_json NVARCHAR(MAX) NOT NULL CHECK (ISJSON(source_json)=1),
    decision NVARCHAR(20) NOT NULL CHECK (decision IN ('held','accepted','corroborated')),
    reason NVARCHAR(1000) NOT NULL,
    session_id NVARCHAR(50) NULL REFERENCES sessions(session_id),
    rider_id NVARCHAR(50) NULL REFERENCES riders(rider_id),
    evidence_url NVARCHAR(1024) NULL,
    decided_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE external_classifications (
    session_id NVARCHAR(50) NOT NULL REFERENCES sessions(session_id),
    rider_id NVARCHAR(50) NOT NULL REFERENCES riders(rider_id),
    candidate_id CHAR(64) NOT NULL UNIQUE REFERENCES external_candidates(candidate_id),
    position INT NOT NULL CHECK (position>0),
    constructor_name NVARCHAR(60) NULL,
    points FLOAT NULL CHECK (points>=0),
    PRIMARY KEY(session_id,rider_id)
);

EXEC(N'CREATE OR ALTER VIEW dbo.vw_effective_classifications AS
SELECT c.session_id,c.rider_id,c.position,c.team_id,c.total_laps,c.time_ms,c.time_text,
       c.gap_first,c.gap_prev,c.best_lap_number,c.best_lap_time,c.top_speed,
       COALESCE(c.points,x.points) AS points,c.status,c.constructor_id,
       COALESCE(c.constructor_name,x.constructor_name) AS constructor_name,c.rider_number,
       CASE WHEN x.session_id IS NOT NULL AND
                      ((c.points IS NULL AND x.points IS NOT NULL) OR
                       (c.constructor_name IS NULL AND x.constructor_name IS NOT NULL))
            THEN ''official-api+external'' ELSE ''official-api'' END AS source_kind
FROM dbo.classifications c
LEFT JOIN dbo.external_classifications x ON x.session_id=c.session_id AND x.rider_id=c.rider_id
    AND x.position=c.position
UNION ALL
SELECT x.session_id,x.rider_id,x.position,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,
       x.points,NULL,NULL,x.constructor_name,NULL,''external''
FROM dbo.external_classifications x
WHERE NOT EXISTS (SELECT 1 FROM dbo.classifications c
                  WHERE c.session_id=x.session_id AND c.rider_id=x.rider_id);');

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
    COALESCE(c.rider_number,r.number) AS rider_number,
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
LEFT JOIN classifications c ON c.session_id=l.session_id AND c.rider_id=l.rider_id
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
    COALESCE(c.rider_number,r.number) AS rider_number,
    r.nationality,
    t.team_name,
    COALESCE(c.constructor_name, t.constructor) AS constructor,
    c.total_laps,
    c.time_text,
    c.gap_first,
    c.best_lap_time,
    c.top_speed,
    c.points,
    c.status
FROM vw_effective_classifications c
JOIN sessions s ON c.session_id = s.session_id
JOIN events e   ON s.event_id = e.event_id
JOIN riders r   ON c.rider_id = r.rider_id
LEFT JOIN teams t ON c.team_id = t.team_id AND t.season_year = e.season_year;
