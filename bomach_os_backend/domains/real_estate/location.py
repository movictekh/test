from collections.abc import Mapping
from math import isfinite

from django.core.exceptions import ValidationError

BOUNDARY_CORNERS = ("nw", "ne", "se", "sw")


def _mapping(value):
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=False)
    if hasattr(value, "dict"):
        return value.dict(exclude_none=False)
    raise ValidationError({"boundary": "Boundary must be a four-corner object."})


def _legacy_list(value):
    if len(value) > 4:
        raise ValidationError({"boundary": "Boundary supports at most four corners."})
    return {
        corner: point
        for corner, point in zip(BOUNDARY_CORNERS, value)
        if point not in (None, {})
    }


def _orientation(a, b, c):
    return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])


def _cross(a, b, c, d):
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def normalize_boundary(value):
    if value in (None, "", [], {}):
        return {}
    raw = _legacy_list(value) if isinstance(value, list) else dict(_mapping(value))
    unknown = sorted(set(raw) - set(BOUNDARY_CORNERS))
    if unknown:
        raise ValidationError({"boundary": f"Unknown boundary corners: {', '.join(unknown)}."})

    result = {}
    for corner in BOUNDARY_CORNERS:
        point = raw.get(corner)
        if point in (None, {}):
            continue
        point = _mapping(point)
        lat, lng = point.get("lat"), point.get("lng")
        lat_missing = lat in (None, "")
        lng_missing = lng in (None, "")
        if lat_missing and lng_missing:
            continue
        if lat_missing or lng_missing:
            raise ValidationError({"boundary": f"{corner.upper()} requires both latitude and longitude."})
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            raise ValidationError({"boundary": f"{corner.upper()} coordinates must be numeric."})
        if not isfinite(lat) or not isfinite(lng):
            raise ValidationError({"boundary": f"{corner.upper()} coordinates must be finite."})
        if not -90 <= lat <= 90:
            raise ValidationError({"boundary": f"{corner.upper()} latitude must be between -90 and 90."})
        if not -180 <= lng <= 180:
            raise ValidationError({"boundary": f"{corner.upper()} longitude must be between -180 and 180."})
        result[corner] = {"lat": lat, "lng": lng}

    points = [(result[c]["lng"], result[c]["lat"]) for c in BOUNDARY_CORNERS if c in result]
    if len(points) != len(set(points)):
        raise ValidationError({"boundary": "Boundary corners must not duplicate coordinates."})
    if len(points) >= 3:
        area2 = 0.0
        for i, point in enumerate(points):
            nxt = points[(i + 1) % len(points)]
            area2 += point[0] * nxt[1] - nxt[0] * point[1]
        if abs(area2) < 1e-12:
            raise ValidationError({"boundary": "Three or more corners must define a non-zero area."})
    if len(points) == 4 and (
        _cross(points[0], points[1], points[2], points[3])
        or _cross(points[1], points[2], points[3], points[0])
    ):
        raise ValidationError({"boundary": "Four corners must follow NW → NE → SE → SW without crossing."})
    return result


def validate_boundary(value):
    return normalize_boundary(value)
