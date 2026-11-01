"""SAM mask records to anchor points. Stdlib plus meta_sam_parser.

Mask raster decodes via the official package. The raster is mask-local, so
the lane-space centroid adds the bounds offset. Verified Oct 27 on a live
lane: mask centroid matched the box centroid to <1 px.
"""

try:
    from meta_sam_parser import decode_mask_to_raster

    _HAS_PARSER = True
except ImportError:
    _HAS_PARSER = False


def mask_centroid(mask_record):
    """Mask record to (cx, cy) centroid in lane pixels."""
    if not _HAS_PARSER:
        raise RuntimeError("meta_sam_parser is not installed")
    raster = decode_mask_to_raster(mask_record.mask)
    w, h = mask_record.mask.width, mask_record.mask.height
    n = sum(raster)
    if n == 0:
        bounds = mask_record.bounds
        return ((bounds.left + bounds.right) / 2.0, (bounds.top + bounds.bottom) / 2.0)
    cx = sum((i % w) for i, v in enumerate(raster) if v) / n
    cy = sum((i // w) for i, v in enumerate(raster) if v) / n
    bounds = mask_record.bounds
    return (bounds.left + cx, bounds.top + cy)


def box_centroid(left, top, right, bottom):
    return ((left + right) / 2.0, (top + bottom) / 2.0)
