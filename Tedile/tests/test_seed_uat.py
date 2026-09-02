import pytest

from types import SimpleNamespace

from database.seed_uat import (
    UAT_MAPPING_MARKER,
    UAT_PASSWORD,
    UAT_CUSTOMERS,
    UAT_PROVIDERS,
    _assert_connected_database,
    _assert_uat_target,
    _is_uat_owned_mapping,
    _mapping_plan,
)


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


def test_only_explicitly_marked_canonical_uat_mapping_is_owned():
    provider = SimpleNamespace(profile_code="UAT-PLUMBER-01")
    owned = SimpleNamespace(get_sub_services=lambda: [UAT_MAPPING_MARKER])
    unknown = SimpleNamespace(get_sub_services=lambda: [])
    assert _is_uat_owned_mapping(provider, owned)
    assert not _is_uat_owned_mapping(provider, unknown)


def test_non_uat_provider_mapping_cannot_be_normalized():
    provider = SimpleNamespace(profile_code="PROVIDER-01")
    marked = SimpleNamespace(get_sub_services=lambda: [UAT_MAPPING_MARKER])
    assert not _is_uat_owned_mapping(provider, marked)


def test_mapping_plan_accepts_intended_mapping_only():
    provider = SimpleNamespace(profile_code="UAT-PLUMBER-01")
    intended = SimpleNamespace(service_id=1, get_sub_services=lambda: [])
    unknown, owned = _mapping_plan(provider, [intended], 1)
    assert unknown == []
    assert owned == []


def test_mapping_plan_rejects_wrong_or_unknown_active_mapping():
    provider = SimpleNamespace(profile_code="UAT-PLUMBER-01")
    wrong = SimpleNamespace(service_id=2, get_sub_services=lambda: [])
    unknown, owned = _mapping_plan(provider, [wrong], 1)
    assert unknown == [wrong]
    assert owned == []


def test_mapping_plan_identifies_only_explicit_uat_owned_extra():
    provider = SimpleNamespace(profile_code="UAT-PLUMBER-01")
    owned = SimpleNamespace(service_id=2, get_sub_services=lambda: [UAT_MAPPING_MARKER])
    unknown, owned_extras = _mapping_plan(provider, [owned], 1)
    assert unknown == []
    assert owned_extras == [owned]


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
