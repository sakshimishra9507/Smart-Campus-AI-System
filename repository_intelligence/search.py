from pathlib import Path
import re

class CodeSearchService:
    def __init__(self, root): self.root=Path(root).resolve()
    def search(self, query, glob=None, max_results=100):
        if not query: return []
        pattern=re.compile(query, re.IGNORECASE)
        results=[]
        paths=self.root.rglob(glob or "*")
        for p in paths:
            if not p.is_file() or any(x in {".git","node_modules",".venv","venv","__pycache__"} for x in p.parts): continue
            try: text=p.read_text(errors="replace")
            except (OSError,UnicodeDecodeError): continue
            for no,line in enumerate(text.splitlines(),1):
                if pattern.search(line):
                    results.append({"path":p.relative_to(self.root).as_posix(),"line":no,"text":line.strip()})
                    if len(results)>=max_results:return results
        return results
