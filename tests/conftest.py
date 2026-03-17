"""Shared pytest configuration and fixtures."""
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests requiring live API access (LSEG Workspace)"
    )
