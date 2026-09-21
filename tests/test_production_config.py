from pathlib import Path
def test_production_files_exist():
    for name in ("Dockerfile","sandbox.Dockerfile","docker-compose.production.yml",".env.example",".env.production.example","docs/deployment.md"):
        assert Path(name).exists()
def test_no_real_secrets_in_examples():
    text=Path(".env.production.example").read_text()
    assert "store-in-secret-manager" in text
    assert "GITHUB_TOKEN=" not in text
def test_compose_has_isolated_sandbox_and_services():
    text=Path("docker-compose.production.yml").read_text()
    assert "network_mode: none" in text and "pids_limit: 64" in text
    for service in ("api:","worker:","postgres:","redis:","sandbox:"): assert service in text
