"""Compatibility shim. Calibration lives in gaze.calibration (core)."""

from gaze.calibration import (  # noqa: F401
    CALIBRATION_GRID,
    DOT_EVERY_S,
    calibration_points,
    dot_error,
    dot_schedule,
    fit_calibration,
)
