from datetime import datetime

import pytest

from tests.conftest import create_isolated_test_app


@pytest.fixture
def app():
    return create_isolated_test_app()


def test_user_datetime_filter_uses_readable_format_without_microseconds(app):
    stored_value = datetime(2026, 8, 23, 11, 0, 44, 412694)

    formatted = app.jinja_env.filters["format_datetime"](stored_value)

    assert formatted == "23 Aug 2026, 11:00 AM"
    assert "412694" not in formatted
    assert str(stored_value) == "2026-08-23 11:00:44.412694"


def test_factory_registers_datetime_filter_on_the_active_jinja_environment(app):
    assert app.jinja_env.filters["format_datetime"] is not None
    assert app.jinja_env.filters["format_datetime"](datetime(2026, 8, 23, 11, 0)) == "23 Aug 2026, 11:00 AM"
