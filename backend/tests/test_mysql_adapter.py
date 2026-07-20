"""Tests for MySQL adapter."""

import pytest

from app.services.mysql_adapter import (
    MySQLDependencyError,
    MySQLSettings,
    build_async_session_factory,
    dependency_status,
)


def test_settings_reject_non_mysql_url_before_optional_import():
    """Settings reject non-MySQL URL before optional import."""
    with pytest.raises(ValueError, match="MYSQL_URL_INVALID"):
        build_async_session_factory(MySQLSettings("sqlite+aiosqlite:///:memory:"))


def test_offline_baseline_reports_missing_driver_without_network_or_install():
    """Offline baseline reports missing driver without network or install."""
    status = dependency_status()
    if not all(status.values()):
        with pytest.raises(MySQLDependencyError, match="MYSQL_DEPENDENCY_MISSING"):
            build_async_session_factory(MySQLSettings("mysql+aiomysql://demo:demo@127.0.0.1:3306/course"))
    else:
        pytest.skip("optional MySQL dependencies are installed in this environment")
