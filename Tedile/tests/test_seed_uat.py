import pytest
from werkzeug.security import check_password_hash

from types import SimpleNamespace

from database.seed_uat import (
    UAT_MAPPING_MARKER,
    UAT_PASSWORD,
    UAT_CUSTOMERS,
    UAT_PROVIDERS,
    CANONICAL_UAT_EMAILS,
    _assert_connected_database,
    _assert_uat_target,
    _is_uat_owned_mapping,
    _mapping_plan,
    _get_or_create_user,
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


class FakeUser:
    def __init__(self, role="customer"):
        self.role = role
        self.password_hash = None
        self.set_password_calls = []

    def set_password(self, password):
        self.set_password_calls.append(password)
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)


class FakeUserQuery:
    def __init__(self, user):
        self.user = user

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return self.user


def test_new_canonical_user_receives_uat_password_hash(monkeypatch):
    created = []

    class UserFactory(FakeUser):
        query = FakeUserQuery(None)

        def __init__(self, **kwargs):
            super().__init__(kwargs["role"])
            created.append(self)

    class FakeSession:
        def add(self, user):
            created.append(user)

        def flush(self):
            return None

    monkeypatch.setattr("database.seed_uat.User", UserFactory)
    monkeypatch.setattr("database.seed_uat.db.session", FakeSession())
    user, reused = _get_or_create_user("uat.customer01@tedile.com", "UAT Customer 1", "customer")
    assert reused is True
    assert check_password_hash(user.password_hash, UAT_PASSWORD)


def test_existing_canonical_user_password_is_reset_when_reused(monkeypatch):
    existing = FakeUser("customer")
    class UserModel(FakeUser):
        query = FakeUserQuery(existing)
    monkeypatch.setattr("database.seed_uat.User", UserModel)
    user, reused = _get_or_create_user("uat.customer01@tedile.com", "UAT Customer 1", "customer")
    assert user is existing
    assert reused is False
    assert check_password_hash(existing.password_hash, UAT_PASSWORD)
    assert existing.set_password_calls == [UAT_PASSWORD]


def test_existing_canonical_user_with_wrong_role_fails_closed(monkeypatch):
    existing = FakeUser("provider")
    class UserModel(FakeUser):
        query = FakeUserQuery(existing)
    monkeypatch.setattr("database.seed_uat.User", UserModel)
    with pytest.raises(RuntimeError, match="unexpected role"):
        _get_or_create_user("uat.customer01@tedile.com", "UAT Customer 1", "customer")
    assert existing.set_password_calls == []


def test_seed_account_definitions_contain_only_canonical_uat_identities():
    emails = {email for email, _name in UAT_CUSTOMERS}
    emails.update(email for _profile, email, _name, _slug, _lat, _lon in UAT_PROVIDERS)
    assert emails
    assert all(email.startswith("uat.") and email.endswith("@tedile.com") for email in emails)
    assert not any(email.endswith("@tedile.test") or email.startswith("dev.") for email in emails)
    assert emails == CANONICAL_UAT_EMAILS


def test_non_canonical_account_is_rejected_before_lookup_or_password_reset(monkeypatch):
    class ExplodingQuery:
        def filter_by(self, **_kwargs):
            raise AssertionError("non-canonical account must be rejected before lookup")

    class UserModel:
        query = ExplodingQuery()

    monkeypatch.setattr("database.seed_uat.User", UserModel)
    with pytest.raises(RuntimeError, match="not canonical"):
        _get_or_create_user("someone@example.com", "Unexpected", "customer")


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
