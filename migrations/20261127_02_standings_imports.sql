IF OBJECT_ID('dbo.standings_imports','U') IS NULL
CREATE TABLE dbo.standings_imports (
    season_year INT NOT NULL,
    category NVARCHAR(20) NOT NULL,
    source_hash CHAR(64) NOT NULL,
    standings_count INT NOT NULL,
    is_final BIT NOT NULL,
    source_url NVARCHAR(1024) NOT NULL,
    source_payload NVARCHAR(MAX) NOT NULL CHECK (ISJSON(source_payload)=1),
    imported_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    PRIMARY KEY (season_year,category)
);
