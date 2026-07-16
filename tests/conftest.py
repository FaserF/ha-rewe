"""Fixtures for REWE Discounts tests."""

import sys
import types
import pytest

# Mock fcntl module for Windows compatibility during Home Assistant test initialization
if sys.platform == "win32":
    fcntl = types.ModuleType("fcntl")
    fcntl.fcntl = lambda *args, **kwargs: 0  # type: ignore[attr-defined]
    fcntl.ioctl = lambda *args, **kwargs: 0  # type: ignore[attr-defined]
    sys.modules["fcntl"] = fcntl

    # Also bypass pytest-socket on Windows to allow loopback socketpairs
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None
    pytest_socket.enable_socket()


@pytest.fixture(autouse=True)
async def enable_custom_integrations(hass):
    """Enable custom integrations to be loaded in tests."""
    hass.data.pop("custom_components", None)
