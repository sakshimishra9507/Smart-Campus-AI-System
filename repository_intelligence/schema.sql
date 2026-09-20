CREATE TABLE IF NOT EXISTS repository_analysis (
 id BIGSERIAL PRIMARY KEY, repository_full_name TEXT NOT NULL, snapshot_sha TEXT NOT NULL, summary JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS repository_file (id BIGSERIAL PRIMARY KEY, analysis_id BIGINT NOT NULL REFERENCES repository_analysis(id) ON DELETE CASCADE, path TEXT NOT NULL, size BIGINT NOT NULL, language TEXT, is_binary BOOLEAN NOT NULL);
CREATE TABLE IF NOT EXISTS repository_dependency (id BIGSERIAL PRIMARY KEY, analysis_id BIGINT NOT NULL REFERENCES repository_analysis(id) ON DELETE CASCADE, name TEXT NOT NULL, version TEXT, manager TEXT NOT NULL, source_file TEXT NOT NULL, is_dev BOOLEAN NOT NULL DEFAULT FALSE);
CREATE TABLE IF NOT EXISTS repository_symbol (id BIGSERIAL PRIMARY KEY, analysis_id BIGINT NOT NULL REFERENCES repository_analysis(id) ON DELETE CASCADE, name TEXT NOT NULL, kind TEXT NOT NULL, path TEXT NOT NULL, line INT NOT NULL, end_line INT NOT NULL);
CREATE TABLE IF NOT EXISTS repository_import (id BIGSERIAL PRIMARY KEY, analysis_id BIGINT NOT NULL REFERENCES repository_analysis(id) ON DELETE CASCADE, source_path TEXT NOT NULL, target TEXT NOT NULL, imported_name TEXT);
CREATE TABLE IF NOT EXISTS repository_route (id BIGSERIAL PRIMARY KEY, analysis_id BIGINT NOT NULL REFERENCES repository_analysis(id) ON DELETE CASCADE, path TEXT NOT NULL, method TEXT NOT NULL, source TEXT NOT NULL, handler TEXT);
CREATE INDEX IF NOT EXISTS idx_repository_file_analysis_path ON repository_file(analysis_id,path);
CREATE INDEX IF NOT EXISTS idx_repository_symbol_analysis_name ON repository_symbol(analysis_id,name);
CREATE INDEX IF NOT EXISTS idx_repository_dependency_analysis_name ON repository_dependency(analysis_id,name);
