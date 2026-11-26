IF OBJECT_ID('dbo.schema_migrations', 'U') IS NULL
    CREATE TABLE dbo.schema_migrations (
        version NVARCHAR(100) NOT NULL PRIMARY KEY,
        applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );

IF COL_LENGTH('dbo.classifications', 'constructor_id') IS NULL
    ALTER TABLE dbo.classifications ADD constructor_id NVARCHAR(50) NULL;
IF COL_LENGTH('dbo.classifications', 'constructor_name') IS NULL
    ALTER TABLE dbo.classifications ADD constructor_name NVARCHAR(60) NULL;

IF OBJECT_ID('dbo.championship_standings', 'U') IS NULL
    CREATE TABLE dbo.championship_standings (
        season_year INT NOT NULL,
        category NVARCHAR(20) NOT NULL,
        rider_id NVARCHAR(50) NOT NULL REFERENCES dbo.riders(rider_id),
        position INT NOT NULL,
        points DECIMAL(10,3) NOT NULL,
        constructor_id NVARCHAR(50) NULL,
        constructor_name NVARCHAR(60) NULL,
        is_final BIT NOT NULL,
        source_url NVARCHAR(1024) NOT NULL,
        source_json NVARCHAR(MAX) NOT NULL CHECK (ISJSON(source_json) = 1),
        fetched_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        PRIMARY KEY (season_year, category, rider_id)
    );

IF OBJECT_ID('dbo.historical_imports', 'U') IS NULL
    CREATE TABLE dbo.historical_imports (
        season_year INT NOT NULL,
        category NVARCHAR(20) NOT NULL,
        source_hash CHAR(64) NOT NULL,
        event_count INT NOT NULL,
        session_count INT NOT NULL,
        classification_count INT NOT NULL,
        standings_count INT NOT NULL,
        source_payload NVARCHAR(MAX) NOT NULL CHECK (ISJSON(source_payload) = 1),
        imported_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        PRIMARY KEY (season_year, category)
    );

EXEC(N'CREATE OR ALTER VIEW dbo.vw_classifications_full AS
SELECT
    e.season_year, e.short_name AS event_short, e.event_name, e.circuit_name,
    s.session_type, s.session_number, s.session_label, s.session_date,
    c.position, r.full_name AS rider, r.number AS rider_number, r.nationality,
    t.team_name, COALESCE(c.constructor_name, t.constructor) AS constructor,
    c.total_laps, c.time_text, c.gap_first, c.best_lap_time, c.top_speed, c.points, c.status
FROM dbo.classifications c
JOIN dbo.sessions s ON c.session_id = s.session_id
JOIN dbo.events e ON s.event_id = e.event_id
JOIN dbo.riders r ON c.rider_id = r.rider_id
LEFT JOIN dbo.teams t ON c.team_id = t.team_id AND t.season_year = e.season_year;');
