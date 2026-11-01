"""T12 live decode: SAM stream -> official parser -> mask centroids.

Usage (PowerShell, .env must hold a real key):
  .\\.venv\\Scripts\\python.exe tools\\t12_live_decode.py [concept]
One live SAM call. Prints records, mask shapes, centroids in lane pixels.
"""

import asyncio
import base64
import io
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_dotenv(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


async def main_async(concept):
    from openai import OpenAI

    key = os.environ.get("MODEL_API_KEY", "")
    base = os.environ.get("META_MODEL_BASE_URL", "https://api.meta.ai/v1").rstrip("/")
    client = OpenAI(base_url=base, api_key=key)

    from PIL import ImageGrab

    shot = ImageGrab.grab()
    shot.thumbnail((1280, 1280))
    buf = io.BytesIO()
    shot.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    print(f"screenshot size={shot.size}", flush=True)

    from meta_sam_parser import CompletedOutcome, video_segmentation_format

    format_ = video_segmentation_format()
    parser = format_.create_parser()
    t0 = time.perf_counter()

    def sync_stream():
        stream = client.responses.create(
            model="sam-3.1",
            stream=True,
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": concept},
                {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"},
            ]}],
        )
        for event in stream:
            yield event

    async def agen():
        for event in sync_stream():
            yield event

    from meta_sam_parser import parse_responses_stream

    parsed = parse_responses_stream(agen(), format_)
    async with parsed:
        async for snapshot in parsed:
            print(f"snapshot rev={snapshot.revision} records={len(snapshot.records)}", flush=True)
    result = await parsed.final_result()
    print(f"secs={time.perf_counter() - t0:.2f} total_records={len(result.records)}")
    for rec in result.records:
        print(f"record type={type(rec).__name__} attrs={[a for a in dir(rec) if not a.startswith('_')][:15]}")
        if type(rec).__name__ == "SegmentationBoxRecord":
            cx = (rec.left + rec.right) / 2.0
            cy = (rec.top + rec.bottom) / 2.0
            print(f"box id={rec.object_id} frame={rec.frame} centroid=({cx:.1f},{cy:.1f}) conf={rec.confidence}")
        if type(rec).__name__ == "SegmentationMaskRecord":
            from meta_sam_parser import decode_mask_to_raster

            raster = decode_mask_to_raster(rec.mask)
            w, h = rec.mask.width, rec.mask.height
            assert len(raster) == w * h, f"raster {len(raster)} != {w}x{h}"
            n = sum(raster)
            cx = sum((i % w) for i, v in enumerate(raster) if v) / n
            cy = sum((i // w) for i, v in enumerate(raster) if v) / n
            print(f"mask id={rec.object_id} size={w}x{h} pixels={n} centroid=({cx:.1f},{cy:.1f}) conf={rec.confidence}")
    return 0


def main():
    load_dotenv(os.path.join(REPO, ".env"))
    concept = sys.argv[1] if len(sys.argv) > 1 else "button"
    return asyncio.run(main_async(concept))


if __name__ == "__main__":
    sys.exit(main())
