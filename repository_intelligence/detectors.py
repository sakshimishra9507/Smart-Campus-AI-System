from pathlib import Path
import json, re
from .models import Dependency, Route
EXT_LANG={".py":"Python",".js":"JavaScript",".jsx":"JavaScript",".ts":"TypeScript",".tsx":"TypeScript",".java":"Java",".go":"Go",".rs":"Rust",".rb":"Ruby",".php":"PHP",".cs":"C#",".cpp":"C++",".c":"C",".html":"HTML",".css":"CSS",".scss":"SCSS",".sql":"SQL",".md":"Markdown",".yml":"YAML",".yaml":"YAML",".json":"JSON",".toml":"TOML"}
CONFIG_NAMES={".env",".env.example","dockerfile","docker-compose.yml","docker-compose.yaml","pyproject.toml","requirements.txt","package.json","tsconfig.json","vite.config.js","vite.config.ts","next.config.js","next.config.mjs","settings.py","alembic.ini"}
def language_for(path): return EXT_LANG.get(Path(path).suffix.lower())
class LanguageDetector:
    def detect(self,files):
        counts={}
        for f in files:
            lang=language_for(f.path)
            if lang and not f.is_binary: counts[lang]=counts.get(lang,0)+1
        return dict(sorted(counts.items(),key=lambda x:(-x[1],x[0])))
class FrameworkDetector:
    def detect(self,root,files,dependencies):
        names={Path(f.path).name.lower() for f in files}; deps={d.name.lower() for d in dependencies}; found=[]
        for name,depnames,markers in [("Django",{"django"},{"manage.py"}),("Flask",{"flask"},set()),("FastAPI",{"fastapi"},set()),("React",{"react"},set()),("Next.js",{"next"},set()),("Vue",{"vue"},set()),("Express",{"express"},set())]:
            if deps&depnames or names&markers: found.append(name)
        return sorted(set(found))
class DependencyAnalyzer:
    def analyze(self,root,files):
        rootp=Path(root); out=[]
        for f in files:
            p=rootp/f.path
            if f.path=="requirements.txt":
                for line in p.read_text(errors="replace").splitlines():
                    line=line.strip()
                    if not line or line.startswith("#") or line.startswith(("-r ","--")): continue
                    m=re.match(r"([A-Za-z0-9_.-]+)\s*(.*)",line)
                    if m: out.append(Dependency(m.group(1),m.group(2).strip() or None,"pip",f.path))
            elif f.path=="pyproject.toml":
                text=p.read_text(errors="replace")
                for m in re.finditer(r"[\"']([A-Za-z0-9_.-]+)(?:[<>=!~][^\"']*)?[\"']",text):
                    if m.group(1).lower() not in {"python","setuptools"}: out.append(Dependency(m.group(1),None,"poetry/pyproject",f.path))
            elif Path(f.path).name=="package.json":
                try:
                    data=json.loads(p.read_text(errors="replace"))
                    for section,dev in (("dependencies",False),("devDependencies",True),("peerDependencies",False)):
                        for name,ver in data.get(section,{}).items(): out.append(Dependency(name,str(ver),"npm",f.path,dev))
                except (json.JSONDecodeError,OSError): pass
        return out
class ConfigurationDetector:
    def detect(self,files): return sorted({f.path for f in files if Path(f.path).name.lower() in CONFIG_NAMES or Path(f.path).name.lower().startswith(".env")})
class EntryPointDetector:
    def detect(self,root,files):
        names={f.path for f in files}; return [p for p in ("manage.py","main.py","app.py","server.py","index.js","index.ts","src/main.py","src/main.ts","src/index.ts","src/index.js","wsgi.py","asgi.py") if p in names]
class TestFrameworkDetector:
    def detect(self,files,dependencies):
        names={d.name.lower() for d in dependencies}; paths=[f.path.lower() for f in files]; found=[]
        if "pytest" in names or any("test_" in p or "/tests/" in p for p in paths): found.append("pytest")
        if "unittest" in names or any(p.endswith("test.py") for p in paths): found.append("unittest")
        if "jest" in names: found.append("Jest")
        if "vitest" in names: found.append("Vitest")
        if "mocha" in names: found.append("Mocha")
        return sorted(set(found))
class APIRouteDetector:
    PY_DJANGO=re.compile(r"path\(\s*[\"']([^\"']+)[\"']\s*,\s*([^,\)]+)")
    PY_DECORATOR=re.compile(r"@(app|router)\.(get|post|put|patch|delete|api_route)\(\s*[\"']([^\"']+)[\"']")
    def detect(self,root,files):
        rootp=Path(root); routes=[]
        for f in files:
            if f.is_binary or Path(f.path).suffix.lower() not in {".py",".js",".ts",".jsx",".tsx"}: continue
            try: text=(rootp/f.path).read_text(errors="replace")
            except OSError: continue
            if Path(f.path).name=="urls.py":
                for m in self.PY_DJANGO.finditer(text): routes.append(Route("/"+m.group(1).lstrip("/"),"ANY",f.path,m.group(2).strip()))
            for m in self.PY_DECORATOR.finditer(text): routes.append(Route(m.group(3),m.group(2).upper(),f.path))
            for m in re.finditer(r"(?:app|router)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)",text): routes.append(Route(m.group(2),m.group(1).upper(),f.path))
        return list(dict.fromkeys(routes))
