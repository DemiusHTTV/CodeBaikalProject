from src.config import load_database_settings


def test_loads_settings_from_env():
    settings = load_database_settings()
    assert settings.host
    assert settings.port > 0
    assert settings.name
    assert settings.user
    assert settings.dsn == (
        f"postgresql://{settings.user}:{settings.password}@{settings.host}:{settings.port}/{settings.name}"
    )
