"""T25: ask Wonder (muse-wonder-1.0) to review the gaze estimator.

Bundles measured data (feature scales, fit quality, failure transcript)
plus the model equations and asks for: physical/optical assessment,
estimator choice, head-pose enrollment protocol, concrete implementable math.

Usage: .\\.venv\\Scripts\\python.exe tools\\wonder_gaze_review.py
"""

import glob
import json
import os
import statistics as st
import sys

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_session(path):
    return [json.loads(line) for line in open(os.path.join(path, "events.jsonl"))]


def summarize(sess):
    evs = load_session(sess)
    t0 = evs[0]["t_mono"]
    cal = [e for e in evs if e["kind"] == "calib"]
    stds = []
    if cal:
        for j in range(7):
            col = [c["payload"]["features"][j] for c in cal]
            mu = sum(col) / len(col)
            stds.append((sum((v - mu) ** 2 for v in col) / len(col)) ** 0.5)
    tr = [e for e in evs if e["kind"] == "trace"]
    xs = [e["payload"]["gaze"][0] for e in tr if e["payload"]["gaze"][0] is not None]
    sels = [(round(e["t_mono"] - t0, 1), e["payload"]["key"],
             e["payload"].get("anchor", "?")) for e in evs if e["kind"] == "selection"]
    quals = [round(e["payload"]["resub_px"]) for e in evs
             if e["kind"] == "calibration_quality"]
    return {"n_calib": len(cal), "feat_stds": [round(s, 4) for s in stds],
            "gaze_x_stdev": round(st.stdev(xs)) if len(xs) > 3 else None,
            "resubs": quals, "selections": sels}


def _load_dotenv(repo):
    path = os.path.join(repo, ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def main():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _load_dotenv(repo)
    sessions = sorted(glob.glob(os.path.join(repo, "data", "beta-*")))
    summary = {os.path.basename(s): summarize(s) for s in sessions[-3:]}
    prompt = """You are reviewing a webcam gaze-estimation subsystem. Be concrete and
mathematical. No encouragement, no generic advice: equations, estimators,
protocols, numbers.

SETUP
- 1280x720 webcam above a 1920x1080 monitor, user ~55cm away, no glasses.
- MediaPipe FaceLandmarker, 478 landmarks, ~30fps, Python, CPU only.
- Features (7): [dxL, dyL, dxR, dyR, head_dx, head_dy, pitch].
  dx/dy = iris-center minus eye-center, normalized by eye width, per eye.
  head_dx/dy = nose minus face-box center, normalized by face size.
  pitch = (nose_y - eye_line_y) / face_height.
- Model: screen_xy = M @ [features, 1], M is 2x8, fit by ridge least squares
  on standardized features (alpha=1.0) over 32 calibration dots (16-pt grid
  x2 passes, each point averaged over 12 frames).
- Online: RLS corrector (forgetting 0.98) fed by sparse exact anchors
  (selected on-screen key centers, residual gate 400px).
- Live pipeline: rolling-5 feature mean, EMA-0.4 output smoothing,
  single-frame jump guard (>400px rejected), EAR-gated (no prediction while
  eyes shut), long-blink 0.6s hold to select.

MEASURED DATA (last 3 beta sessions, monitor x in 1920..3840)
""" + json.dumps(summary, indent=1) + """

KNOWN FACTS
- Calibration resub error ~230-270px on a 1920px-wide screen.
- Feature stds during static calibration: iris ~0.03-0.06, head_dx ~0.02,
  head_dy/pitch ~0.005 (near-constant: user does not move head on dots).
- Raw fit coefficients reach +-55000 on low-variance columns; ridge 1.0
  brings max to ~25000. Blink-transition frames (half-closed lid distorts
  iris landmarks) used to explode predictions thousands of px; jump guard
  now rejects them.
- Failure mode now: map works near calibration posture, breaks when the
  user rotates/translates head naturally ("1mm and everything is off",
  keys become unreachable, map bias shifts ~1 key between refits).
- Human closes the loop: user watches the highlight and steers gaze until
  it sits on the intended key, then holds eyes shut 0.6s.

PROPOSAL ON THE TABLE (from the builder)
- Biometric-style enrollment sweep at start: fix gaze on one dot while
  slowly rotating head left/right/up/down, leaning forward/back, blinking.
  Goal: teach the model invariance to head motion (same screen point under
  varied pose), like biometric capture.

QUESTIONS
1. Is the linear-affine model class the right choice at all here? Given the
   perspective projection of a rotating eyeball plus head motion, what is
   the minimum model class (quadratic features? head-normalized features?
   per-region local fits? tiny MLP?) that fixes posture fragility while
   staying fittable from ~1-2 min of enrollment + sparse anchors? Rank by
   expected error reduction vs implementation cost.
2. Write the exact feature normalization / estimator math you recommend
   (fit equations + online update), with concrete constants justified from
   the data above (feature stds, resub, coefficient magnitudes).
3. Design the enrollment protocol precisely: which motions, how many
   samples each, gaze fixed or varied per motion, total time. Explain what
   each motion identifies mathematically (which nullspace / parameter).
4. The anchors-vs-gate tension: exact key-center anchors with 400px gate
   and fast RLS prior now oscillate (applied/rejected alternating) and one
   accidental selection poisons the map. Propose the correct gating /
   weighting scheme with numbers.
5. What is the single biggest modeling mistake in the current pipeline?
   Name it in one sentence, then the fix in one paragraph.

Limit: 900 words. Use headers Q1..Q5.
"""
    client = OpenAI(base_url=os.environ.get("META_MODEL_BASE_URL",
                                            "https://api.meta.ai/v1"),
                    api_key=os.environ["MODEL_API_KEY"], timeout=180.0)
    r = client.responses.create(model="muse-wonder-1.0", input=prompt,
                                reasoning={"effort": "medium"},
                                max_output_tokens=9000)
    if not (r.output_text or "").strip():
        print("empty output_text - dump:")
        print(r.model_dump_json(indent=1)[:4000])
    else:
        print(r.output_text)
    print(f"\n[usage: {r.usage}]")


if __name__ == "__main__":
    sys.exit(main())
