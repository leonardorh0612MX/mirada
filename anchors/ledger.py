"""Anchor ledger: every proposal, accepted or not, with its gate verdict.

The ledger is the audit trail for anchor precision (EVAL.md). Storage is a
plain list of dicts; persistence goes through recorder session events.
"""

_next_id = [0]


def make_anchor(source, x, y, confidence, reason, t_mono, origin=None):
    """Build one anchor proposal. No validation beyond types."""
    _next_id[0] += 1
    return {
        "id": _next_id[0],
        "t_mono": t_mono,
        "source": source,  # caret | click | spark | sam
        "x": x,
        "y": y,
        "confidence": confidence,
        "reason": reason,
        "origin": origin or {},
        "verdict": None,
        "verdict_reason": None,
    }


class AnchorLedger:
    def __init__(self):
        self.anchors = []

    def propose(self, anchor):
        self.anchors.append(anchor)
        return anchor["id"]

    def resolve(self, anchor_id, accepted, reason):
        for a in self.anchors:
            if a["id"] == anchor_id:
                a["verdict"] = "accepted" if accepted else "rejected"
                a["verdict_reason"] = reason
                return a
        raise KeyError(f"unknown anchor id {anchor_id}")

    def accepted(self):
        return [a for a in self.anchors if a["verdict"] == "accepted"]

    def precision(self, ground_truth, threshold_px):
        """Fraction of accepted anchors within threshold of ground truth.

        ground_truth: dict anchor_id -> (x, y). Anchors without ground truth
        are excluded, never counted as correct.
        """
        hits, total = 0, 0
        for a in self.accepted():
            if a["id"] not in ground_truth:
                continue
            gx, gy = ground_truth[a["id"]]
            dist = ((a["x"] - gx) ** 2 + (a["y"] - gy) ** 2) ** 0.5
            total += 1
            if dist <= threshold_px:
                hits += 1
        return hits / total if total else 0.0
