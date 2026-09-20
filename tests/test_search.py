from repository_intelligence.search import CodeSearchService

def test_code_search(tmp_path):
    (tmp_path/"a.py").write_text("def hello():\n    return 'hello'\n")
    result=CodeSearchService(str(tmp_path)).search("hello")
    assert len(result)==2
    assert result[0]["path"]=="a.py"
