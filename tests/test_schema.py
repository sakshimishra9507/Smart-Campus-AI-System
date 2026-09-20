from pathlib import Path

def test_schema_exists():
    schema=Path(__file__).parents[1]/"repository_intelligence"/"schema.sql"
    text=schema.read_text()
    assert "repository_analysis" in text
    assert "repository_symbol" in text
    assert "repository_import" in text
