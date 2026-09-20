from pathlib import Path
from repository_intelligence.analyzer import RepositoryAnalyzer
from repository_intelligence.detectors import LanguageDetector, DependencyAnalyzer
from repository_intelligence.scanner import RepositoryScanner


def make_repo(tmp_path):
    (tmp_path/"requirements.txt").write_text("Django==5.2\npytest>=8\n")
    (tmp_path/"manage.py").write_text("print('x')")
    (tmp_path/"urls.py").write_text("from django.urls import path\nurlpatterns=[path('api/users/', view)]")
    (tmp_path/"app.py").write_text("def hello():\n    return 1\n\nclass Service:\n    pass\n")
    (tmp_path/"tests").mkdir(); (tmp_path/"tests/test_app.py").write_text("def test_hello(): pass")


def test_scanner_and_language_detection(tmp_path):
    files,_=RepositoryScanner().scan(str(tmp_path))
    assert {f.path for f in files} >= {"app.py","urls.py","requirements.txt"}
    assert LanguageDetector().detect(files)["Python"] >= 3


def test_dependency_detection(tmp_path):
    make_repo(tmp_path)
    files,_=RepositoryScanner().scan(str(tmp_path))
    deps=DependencyAnalyzer().analyze(str(tmp_path),files)
    assert {d.name for d in deps} >= {"Django","pytest"}


def test_full_analysis(tmp_path):
    make_repo(tmp_path)
    a=RepositoryAnalyzer(str(tmp_path)).analyze()
    assert "Python" in a.languages
    assert "Django" in a.frameworks
    assert "pytest" in a.test_frameworks
    assert "manage.py" in a.entry_points
    assert any(s.name=="hello" for s in a.symbols)
    assert any(r.path=="/api/users/" for r in a.routes)
