# -*- coding: utf-8 -*-
"""
Google Earth Engine authentication and initialisation helpers.
"""

import os


def check_ee_installed():
    """Return (ok: bool, message: str)."""
    try:
        import ee  # noqa: F401
        return True, "earthengine-api is installed."
    except ImportError:
        return False, (
            "earthengine-api is not installed.\n\n"
            "Install it by running the following command in the "
            "OSGeo4W Shell (as Administrator):\n\n"
            "    pip install earthengine-api\n\n"
            "Then restart QGIS."
        )


def authenticate():
    """
    Launch the GEE OAuth browser flow.
    Returns (ok, message).
    """
    ok, msg = check_ee_installed()
    if not ok:
        return False, msg
    try:
        import ee
        ee.Authenticate()
        return True, "Authentication complete."
    except Exception as e:
        return False, f"Authentication failed: {e}"


def initialize(project=None):
    """
    Initialise the GEE session.
    project: optional GEE cloud project id (required for new API).
    Returns (ok, message).
    """
    ok, msg = check_ee_installed()
    if not ok:
        return False, msg
    try:
        import ee
        kwargs = {}
        if project:
            kwargs["project"] = project
        ee.Initialize(**kwargs)
        # Quick connectivity test
        _ = ee.Number(1).getInfo()
        return True, "Connected to Google Earth Engine."
    except Exception as e:
        return False, f"GEE initialisation failed: {e}"


def is_initialized():
    """Return True if a GEE session is already active."""
    try:
        import ee
        ee.Number(1).getInfo()
        return True
    except Exception:
        return False
