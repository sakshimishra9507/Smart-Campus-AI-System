from pathlib import Path
import json

SCHEMA_PATH=Path(__file__).with_name("schema.sql")

class PostgresRepositoryStore:
    """Persistence adapter. It never executes repository code."""
    def __init__(self, dsn): self.dsn=dsn
    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("PostgreSQL persistence requires psycopg[binary].") from exc
        return psycopg.connect(self.dsn)
    def ensure_schema(self):
        with self._connect() as conn:
            conn.execute(SCHEMA_PATH.read_text())
    def save(self, repository_full_name, snapshot_sha, analysis):
        payload=json.dumps(analysis.architecture_summary)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO repository_analysis(repository_full_name,snapshot_sha,summary) VALUES (%s,%s,%s) RETURNING id",(repository_full_name,snapshot_sha,payload))
                analysis_id=cur.fetchone()[0]
                for f in analysis.files: cur.execute("INSERT INTO repository_file(analysis_id,path,size,language,is_binary) VALUES (%s,%s,%s,%s,%s)",(analysis_id,f.path,f.size,f.language,f.is_binary))
                for d in analysis.dependencies: cur.execute("INSERT INTO repository_dependency(analysis_id,name,version,manager,source_file,is_dev) VALUES (%s,%s,%s,%s,%s,%s)",(analysis_id,d.name,d.version,d.manager,d.source_file,d.dev))
                for s in analysis.symbols: cur.execute("INSERT INTO repository_symbol(analysis_id,name,kind,path,line,end_line) VALUES (%s,%s,%s,%s,%s,%s)",(analysis_id,s.name,s.kind,s.path,s.line,s.end_line))
                for i in analysis.imports: cur.execute("INSERT INTO repository_import(analysis_id,source_path,target,imported_name) VALUES (%s,%s,%s,%s)",(analysis_id,i.source,i.target,i.imported_name))
                for r in analysis.routes: cur.execute("INSERT INTO repository_route(analysis_id,path,method,source,handler) VALUES (%s,%s,%s,%s,%s)",(analysis_id,r.path,r.method,r.source,r.handler))
            conn.commit()
        return analysis_id
