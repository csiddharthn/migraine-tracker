from pathlib import Path

LAUNCHER_PATH = Path("scripts/launch_app.ps1")
INITIAL_SETUP_PATH = Path("scripts/initial_setup.ps1")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_launcher_constructs_local_database_urls_from_postgres_password():
    launcher = _text(LAUNCHER_PATH)
    assert '[System.Uri]::EscapeDataString($env:POSTGRES_PASSWORD)' in launcher
    assert 'postgresql+psycopg://migraine:$encodedPassword@127.0.0.1:5433/migraine_tracker' in launcher
    assert 'postgresql+psycopg://migraine:$encodedPassword@127.0.0.1:5433/migraine_tracker_test' in launcher


def test_launcher_does_not_trust_stale_database_url_from_env_file():
    launcher = _text(LAUNCHER_PATH)
    assert 'foreach ($name in @("POSTGRES_PASSWORD"))' in launcher
    assert 'foreach ($name in @("POSTGRES_PASSWORD", "MIGRAINE_DATABASE_URL", "MIGRAINE_TEST_DATABASE_URL"))' not in launcher


def test_launcher_uses_local_auth_config_or_documented_defaults():
    launcher = _text(LAUNCHER_PATH)
    assert 'Get-EnvFileValue -Path $repoEnvFile -Name "AUTH_USERNAME"' in launcher
    assert 'Get-EnvFileValue -Path $repoEnvFile -Name "AUTH_PASSWORD"' in launcher
    assert '$env:AUTH_USERNAME = if ([string]::IsNullOrWhiteSpace($configuredUsername)) { "admin" }' in launcher
    assert '$env:AUTH_PASSWORD = if ([string]::IsNullOrWhiteSpace($configuredPassword)) { "migraine" }' in launcher
    assert "Import-AuthenticationEnvironment" in launcher


def test_initial_setup_constructs_local_database_urls_from_postgres_password():
    initial_setup = _text(INITIAL_SETUP_PATH)
    assert '[System.Uri]::EscapeDataString($env:POSTGRES_PASSWORD)' in initial_setup
    assert 'postgresql+psycopg://migraine:$encodedPassword@127.0.0.1:5433/migraine_tracker' in initial_setup
    assert 'postgresql+psycopg://migraine:$encodedPassword@127.0.0.1:5433/migraine_tracker_test' in initial_setup
