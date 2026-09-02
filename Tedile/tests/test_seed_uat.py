import pytest

from database.seed_uat import UAT_PASSWORD, UAT_CUSTOMERS, UAT_PROVIDERS, _assert_connected_database, _assert_uat_target


class FakeApp:
    def __init__(self, **values):
        self.config = values


def uat_app(**overrides):
    values = {
        "APP_ENV": "uat",
        "SQLALCHEMY_DATABASE_URI": "postgresql://uat_runner:password@uat-db.internal:5432/tedile_uat",
        "UAT_DATABASE_NAME": "tedile_uat",
    }
    values.update(overrides)
    return FakeApp(**values)


def test_uat_guard_accepts_explicit_remote_uat_database():
    _assert_uat_target(uat_app())
    _assert_connected_database(uat_app(), "tedile_uat")


def test_uat_credentials_are_the_approved_synthetic_accounts():
    assert UAT_PASSWORD == "Test@1234"
    assert {email for email, _name in UAT_CUSTOMERS} == {
        "uat.customer01@tedile.com",
        "uat.customer02@tedile.com",
        "uat.customer03@tedile.com",
    }
    assert {email for _profile, email, _name, _slug, _lat, _lon in UAT_PROVIDERS} == {
        "uat.plumber01@tedile.com",
        "uat.electrician01@tedile.com",
        "uat.welder01@tedile.com",
        "uat.acrepair01@tedile.com",
    }


@pytest.mark.parametrize("overrides", [
    {"APP_ENV": "development"},
    {"APP_ENV": "production"},
    {"SQLALCHEMY_DATABASE_URI": "postgresql://uat_runner:password@uat-db.internal:5432/tedile_dev"},
    {"SQLALCHEMY_DATABASE_URI": "postgresql://tedile_local:password@uat-db.internal:5432/tedile_uat"},
    {"SQLALCHEMY_DATABASE_URI": "sqlite:///tedile_uat.db"},
    {"UAT_DATABASE_NAME": None},
    {"SQLALCHEMY_DATABASE_URI": "postgresql://uat_runner:password@localhost:5432/tedile_uat"},
    {"SQLALCHEMY_DATABASE_URI": "postgresql://uat_runner:password@uat-db.internal:5432/development_uat"},
])
def test_uat_guard_rejects_unsafe_or_ambiguous_targets(overrides):
    with pytest.raises(RuntimeError):
        _assert_uat_target(uat_app(**overrides))


def test_connected_database_must_match_explicit_uat_name():
    with pytest.raises(RuntimeError):
        _assert_connected_database(uat_app(), "another_uat")
