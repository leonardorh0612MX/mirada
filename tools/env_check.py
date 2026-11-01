"""Environment check: light, face size, estimated distance. Reusable.

distance_cm is an ESTIMATE (Plausible, not verified): focal length assumed
from a typical 78 deg HFOV at the frame width, face width assumed 140 mm
(population average). Expect +-15%. Good for degrees context, not metrology.
"""

FOCAL_PX_PER_WIDTH = 0.617  # f = (W/2) / tan(39deg) ~ 0.617 * W
FACE_WIDTH_MM = 140.0


def estimate_distance_cm(face_width_px, frame_width_px):
    """Face width in px to camera distance in cm (estimate)."""
    if face_width_px <= 0 or frame_width_px <= 0:
        return None
    focal_px = FOCAL_PX_PER_WIDTH * frame_width_px
    return (focal_px * FACE_WIDTH_MM) / face_width_px / 10.0


def light_label(brightness):
    if brightness < 50:
        return "dark"
    if brightness < 120:
        return "ok"
    return "bright"


def expected_conditions(brightness, distance_cm):
    """Startup gate: returns list of warnings (empty means good to record)."""
    warn = []
    if brightness < 50:
        warn.append(f"low light ({brightness:.0f}/255): add frontal light")
    if distance_cm is not None and not (40 <= distance_cm <= 80):
        warn.append(f"distance ~{distance_cm:.0f} cm: aim for 50-70 cm")
    return warn
