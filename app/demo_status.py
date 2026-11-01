"""Demo status model: every failure has a visible state and a recovery path.

Pure logic. The GUI renders status.message and status.banner; this module
decides what they say. Priority: api_down > no_face > low_light > ok.
Recovery is automatic: healthy inputs return the status to ok.
"""

OK = "ok"
NO_FACE = "no_face"
LOW_LIGHT = "low_light"
API_DOWN = "api_down"

MESSAGES = {
    OK: "Tracking. Look at the highlighted target.",
    NO_FACE: "No face detected. Center yourself in the camera.",
    LOW_LIGHT: "Low light. Face tracking is degraded.",
    API_DOWN: "Semantic anchors paused (no connection). Basic tracking continues.",
}


class DemoStatus:
    def __init__(self, brightness_threshold=40.0, face_grace_s=1.5):
        self.brightness_threshold = brightness_threshold
        self.face_grace_s = face_grace_s
        self.state = OK
        self._last_face_t = None

    @property
    def message(self):
        return MESSAGES[self.state]

    @property
    def banner(self):
        return self.state != OK

    def update(self, face_present, brightness, api_ok, t_mono):
        """Advance the status. Returns the new state string."""
        if face_present:
            self._last_face_t = t_mono
        face_lost = (
            self._last_face_t is None
            or (t_mono - self._last_face_t) > self.face_grace_s
        )
        if not api_ok:
            self.state = API_DOWN
        elif face_lost:
            self.state = NO_FACE
        elif brightness < self.brightness_threshold:
            self.state = LOW_LIGHT
        else:
            self.state = OK
        return self.state
