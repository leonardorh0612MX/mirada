# Mirada — hackathon submission (copy-paste source)

Video title, form fields and survey answers. Fenced blocks are
ready to paste verbatim.

## Video title

```text
Mirada — Look + Hold to Speak: Full Computer Control from a $30 Webcam
```

## Most Viral Track — X post

Post from your account, then paste the post link in the form:

```text
I built Mirada — full computer control from a $30 webcam. Look + hold to speak, type, and drive any app. No headset, no $5k tracker. Built 100% on Meta AI models.

🎥 [tu link de YouTube]
💻 https://github.com/leonardorh0612MX/mirada
```

## Project Description

```text
Mirada is a new answer to the oldest problem in cheap eye tracking: drift. Webcam gaze degrades within minutes because one-pose calibration memorizes a single head position — move a millimeter and the map is wrong. Our innovation, semantic recalibration, closes that loop: a local ~30fps gaze model corrected by sparse semantic anchors. Muse Spark reads screenshots plus interaction context and infers where you almost certainly looked; SAM 3.1 pinpoints it to the pixel; a tiny bias-only online corrector absorbs the fix — never an LLM per frame. Sessions replay offline under competing strategies (pilot, n=2: anchors cut mean error 406→397px while uncorrected drift explodes 63→941px in 15 min). The same anchors could correct headset gaze drift next.

The innovation ships as a gaze communication board on an ordinary $30 webcam: look at a cell, close your eyes ~0.4s, and the computer speaks. Eight huge phrase cells with offline speech (EN/ES, editable), a full gaze keyboard with word completion and SEND, and an APPS page launching real apps (YouTube, browser, Discord…) where your gaze becomes the mouse — look freely, close to click — plus a floating dock to return anytime. The caregiver's mouse always works alongside.

Built for people who depend on gaze — ALS, spinal injury, motor impairments — replacing $5,000 dedicated trackers with hardware they already own. Fully offline live loop, no API key needed: any judge can verify it with any webcam. Paper draft and replay harness ship in the repo.
```

## Public GitHub Repository

```text
https://github.com/leonardorh0612MX/mirada
```

## 3-Minute Demo Video

Your unlisted YouTube link (verified in a private window). NOT the
repo URL.

## Describe your use of Meta products

```text
100% of this project's AI runs on Meta. muse-spark-1.3 (Meta Model API, OpenAI-compatible + Responses): reads session screenshots plus interaction context and proposes semantic anchors — {concept, confidence, reason} for where the user almost certainly looked (tools/gen_anchors.py, offline after recording). sam-3.1 (Responses API): localizes each proposed concept to a pixel box/centroid on the screenshot (strategy D; median error ~1px on UI targets). muse-spark-open via Baseten (OpenAI-compatible): high-volume backend carrying the bulk anchor-generation runs (--backend baseten). muse-wonder-1.0: design-time architecture review — its gaze-map analysis (fixed physical scales, interaction terms, bias-only online updates, consensus gating) reshaped our calibration math and enrollment protocol. muse-image-1.0: README/site artwork, committed under site/. Deliberately, the shipped live loop calls no model at all: Meta models provide labels offline, local math (affine map + bias corrector) does the correction at ~30fps — that separation is the thesis, and why the app runs for judges with no API key.
```

## Why are Meta's models important to your solution?

```text
Without screen-understanding models there is no Mirada — only another click-calibrated tracker. The differentiator, semantic anchors, exists solely because a multimodal model can look at a screenshot and infer gaze targets (caret, clicked control, instruction block) that clicks and mouse position never reveal. Spark-1.3 made that labeling fast and cheap enough to run over full sessions; SAM 3.1 turned vague concepts into pixel-exact corrections; Spark-open weights on Baseten made high-volume runs affordable; Wonder-1.0's reasoning fixed our gaze math before we wasted days. Meta's stack is the correction signal; everything local just applies it.
```

## Partner feedback (max 150 chars)

```text
Baseten: OpenAI-compatible Spark-open at high volume, zero friction; carried our anchor runs.
```

## Scales and consent

- How likely to build with Meta Model API → top of scale.
- Overall opinion of Meta Model API → best option.
- Use/promotion consent → accept (required).
- Recommend Meta Model API → 9–10.
- Recommend Muse Code → 10 (the whole repo was pair-built with it).

## Survey

- Biggest obstacle:

```text
Webcam gaze collapsed with head motion: one-pose calibration memorized unidentifiable head coefficients, so 1mm of movement destroyed accuracy. Fixed with factorial gaze×posture enrollment plus bias-only online correction.
```

- Compared with other models:

```text
All-in on Meta per the rules: Spark gave fast cheap screenshot understanding, Wonder's review reshaped our math, SAM boxes hit ~1px median. On par with the OpenAI/Anthropic APIs we use at work, at lower cost.
```

- What matters most when choosing:

```text
Accuracy per dollar at low latency, plus a standard API shape so switching costs nothing.
```

- Hardest to switch:

```text
Per-family prompt tuning; OpenAI-compatible APIs make the mechanics trivial.
```

- Production blocker for Meta's models:

```text
Committed pricing, uptime SLA, and rate limits for always-on assistive use.
```

## Before hitting submit

1. Credential Manager → `git push` (public repo must have D41–D43).
2. README: swap the video note for the real link (own commit + push).
3. Submit before 7PM ET Nov 4; save the confirmation screenshot.
