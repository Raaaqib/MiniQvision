"""
Raaqib NVR - Zone geometry utilities.
Point-in-polygon test using the ray-casting algorithm.
"""

from __future__ import annotations


def point_in_polygon(px: float, py: float, polygon: list) -> bool:
    """
    Ray-casting point-in-polygon test.
    polygon: list of ZonePoint (with .x and .y attributes)
    Returns True if (px, py) is inside the polygon.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i].x, polygon[i].y
        xj, yj = polygon[j].x, polygon[j].y
        if ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi + 1e-10) + xi
        ):
            inside = not inside
        j = i
    return inside


def bbox_center(bbox: tuple) -> tuple[float, float]:
    """
    Returns (cx, cy) center of a bbox.
    bbox format: (x1, y1, x2, y2) - top-left and bottom-right corners.
    """
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def filter_detections_by_zones(
    detections: list,
    zones: list,
    camera_id: str = "",
) -> list:
    """
    Apply exclusion and trigger zone filtering to detections.
    Returns a new list and never mutates the input list.
    """
    if not zones:
        return detections

    exclude_zones = [z for z in zones if z.type == "exclude" and z.active]
    trigger_zones = [z for z in zones if z.type == "trigger" and z.active]

    if not exclude_zones and not trigger_zones:
        return detections

    kept = []
    for det in detections:
        cx, cy = bbox_center(det.bbox)
        label = det.label

        excluded = False
        for zone in exclude_zones:
            if zone.classes and label not in zone.classes:
                continue
            if point_in_polygon(cx, cy, zone.polygon):
                excluded = True
                break

        if excluded:
            continue

        applicable_triggers = [
            z for z in trigger_zones
            if not z.classes or label in z.classes
        ]

        if applicable_triggers:
            inside_any = any(
                point_in_polygon(cx, cy, z.polygon)
                for z in applicable_triggers
            )
            if not inside_any:
                continue

        kept.append(det)

    return kept
