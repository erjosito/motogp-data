IF COL_LENGTH('dbo.classifications', 'rider_number') IS NULL
    ALTER TABLE dbo.classifications ADD rider_number INT NULL;
IF COL_LENGTH('dbo.sessions', 'source_kind') IS NULL
    ALTER TABLE dbo.sessions ADD source_kind NVARCHAR(30) NOT NULL
        CONSTRAINT DF_sessions_source_kind DEFAULT 'official-api';

IF OBJECT_ID('dbo.external_sources', 'U') IS NULL
    CREATE TABLE dbo.external_sources (
        source_id NVARCHAR(80) NOT NULL PRIMARY KEY,
        source_url NVARCHAR(1024) NOT NULL,
        declared_license NVARCHAR(100) NOT NULL,
        content_hash CHAR(64) NOT NULL,
        fetched_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );

IF OBJECT_ID('dbo.external_candidates', 'U') IS NULL
    CREATE TABLE dbo.external_candidates (
        candidate_id CHAR(64) NOT NULL PRIMARY KEY,
        source_id NVARCHAR(80) NOT NULL REFERENCES dbo.external_sources(source_id),
        season_year INT NOT NULL,
        category NVARCHAR(20) NOT NULL,
        event_short NVARCHAR(10) NOT NULL,
        rider_name NVARCHAR(100) NOT NULL,
        source_json NVARCHAR(MAX) NOT NULL CHECK (ISJSON(source_json)=1),
        decision NVARCHAR(20) NOT NULL CHECK (decision IN ('held','accepted','corroborated')),
        reason NVARCHAR(1000) NOT NULL,
        session_id NVARCHAR(50) NULL REFERENCES dbo.sessions(session_id),
        rider_id NVARCHAR(50) NULL REFERENCES dbo.riders(rider_id),
        evidence_url NVARCHAR(1024) NULL,
        decided_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );

IF OBJECT_ID('dbo.external_classifications', 'U') IS NULL
    CREATE TABLE dbo.external_classifications (
        session_id NVARCHAR(50) NOT NULL REFERENCES dbo.sessions(session_id),
        rider_id NVARCHAR(50) NOT NULL REFERENCES dbo.riders(rider_id),
        candidate_id CHAR(64) NOT NULL UNIQUE REFERENCES dbo.external_candidates(candidate_id),
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
            THEN ''official-api+external''
            ELSE ''official-api'' END AS source_kind
FROM dbo.classifications c
LEFT JOIN dbo.external_classifications x ON x.session_id=c.session_id AND x.rider_id=c.rider_id
    AND x.position=c.position
UNION ALL
SELECT x.session_id,x.rider_id,x.position,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,
       x.points,NULL,NULL,x.constructor_name,NULL,''external''
FROM dbo.external_classifications x
WHERE NOT EXISTS (SELECT 1 FROM dbo.classifications c
                  WHERE c.session_id=x.session_id AND c.rider_id=x.rider_id);');
