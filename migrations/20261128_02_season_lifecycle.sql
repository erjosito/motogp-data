IF OBJECT_ID('dbo.season_lifecycle', 'U') IS NULL
CREATE TABLE dbo.season_lifecycle (
    season_year INT NOT NULL,
    category NVARCHAR(20) NOT NULL,
    standings_hash CHAR(64) NOT NULL,
    import_kind NVARCHAR(20) NOT NULL CHECK (import_kind IN ('standings', 'historical')),
    import_hash CHAR(64) NOT NULL,
    other_import_hash CHAR(64) NULL,
    evidence_url NVARCHAR(2048) NOT NULL,
    evidence_hash CHAR(64) NOT NULL,
    review_note NVARCHAR(2000) NOT NULL,
    confirmed_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    invalidated_at DATETIME2 NULL,
    invalidation_reason NVARCHAR(200) NULL,
    PRIMARY KEY (season_year, category)
);
