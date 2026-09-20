from pathlib import Path
from .scanner import RepositoryScanner
from .detectors import LanguageDetector,FrameworkDetector,DependencyAnalyzer,ConfigurationDetector,EntryPointDetector,TestFrameworkDetector,APIRouteDetector,language_for
from .symbols import SymbolIndexer
from .models import RepositoryAnalysis

class RepositoryAnalyzer:
    def __init__(self, root, scanner=None):
        self.root=str(Path(root).resolve()); self.scanner=scanner or RepositoryScanner()
        self.languages=LanguageDetector(); self.frameworks=FrameworkDetector(); self.dependencies=DependencyAnalyzer(); self.config=ConfigurationDetector(); self.entry=EntryPointDetector(); self.tests=TestFrameworkDetector(); self.routes=APIRouteDetector(); self.symbols=SymbolIndexer()
    def analyze(self):
        files,dirs=self.scanner.scan(self.root)
        enriched=[type(f)(f.path,f.size,language_for(f.path),f.is_binary) for f in files]
        deps=self.dependencies.analyze(self.root,enriched)
        analysis=RepositoryAnalysis(self.root,enriched,dirs,self.languages.detect(enriched),self.frameworks.detect(self.root,enriched,deps),self._package_managers(enriched),deps,self.config.detect(enriched),self.entry.detect(self.root,enriched),self.tests.detect(enriched,deps),self.routes.detect(self.root,enriched),[],[])
        analysis.symbols,analysis.imports=self.symbols.index(self.root,enriched)
        analysis.architecture_summary=self._summary(analysis)
        return analysis
    def _package_managers(self,files):
        names={Path(f.path).name for f in files}; found=[]
        if "requirements.txt" in names or "pyproject.toml" in names: found.append("pip/pyproject")
        if "package.json" in names:
            if "pnpm-lock.yaml" in names: found.append("pnpm")
            elif "yarn.lock" in names: found.append("yarn")
            else: found.append("npm")
        if "poetry.lock" in names: found.append("poetry")
        return sorted(set(found))
    def _summary(self,a):
        return {"files":len(a.files),"directories":len(a.directories),"languages":a.languages,"frameworks":a.frameworks,"package_managers":a.package_managers,"dependency_count":len(a.dependencies),"configuration_count":len(a.configurations),"entry_points":a.entry_points,"test_frameworks":a.test_frameworks,"api_route_count":len(a.routes),"symbol_count":len(a.symbols),"import_count":len(a.imports),"top_level_directories":sorted({p.split('/')[0] for p in a.directories if p})}
