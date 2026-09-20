from pathlib import Path
import ast,re
from .models import Symbol, ImportRelation
class SymbolIndexer:
    def index(self,root,files):
        rootp=Path(root); symbols=[]; imports=[]
        for f in files:
            if f.is_binary: continue
            p=rootp/f.path
            try: text=p.read_text(errors="replace")
            except OSError: continue
            if p.suffix==".py":
                try: tree=ast.parse(text,filename=f.path)
                except SyntaxError: continue
                for n in ast.walk(tree):
                    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): symbols.append(Symbol(n.name,"class" if isinstance(n,ast.ClassDef) else "function",f.path,n.lineno,getattr(n,"end_lineno",n.lineno)))
                    elif isinstance(n,ast.Import):
                        for a in n.names: imports.append(ImportRelation(f.path,a.name,a.asname))
                    elif isinstance(n,ast.ImportFrom): imports.append(ImportRelation(f.path,n.module or "","".join(a.name for a in n.names)))
            elif p.suffix.lower() in {".js",".jsx",".ts",".tsx"}:
                for m in re.finditer(r"\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)|\bclass\s+([A-Za-z_$][\w$]*)",text):
                    name=m.group(1) or m.group(2); symbols.append(Symbol(name,"function" if m.group(1) else "class",f.path,text.count("\n",0,m.start())+1,text.count("\n",0,m.end())+1))
                for m in re.finditer(r"(?:import.*?from\s*|require\(\s*)[\"']([^\"']+)[\"']",text): imports.append(ImportRelation(f.path,m.group(1)))
        return symbols,imports
