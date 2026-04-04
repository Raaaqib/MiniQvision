"""
LPR Zone — polygon-based region of interest per camera.
A detection is only passed to LPR if the vehicle centroid (or bbox center)
falls inside at least one configured zone polygon.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import cv2
import numpy as np


Point = Tuple[float, float]
Polygon = List[Point]


@dataclass
class LPRZone:
    id: str
    polygon: Polygon                      # list of (x, y) in pixel coords
    _np_poly: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        self._np_poly = np.array(self.polygon, dtype=np.float32)

    # ------------------------------------------------------------------
    def contains(self, x: float, y: float) -> bool:
        """Return True if point (x, y) is inside the polygon."""
        result = cv2.pointPolygonTest(self._np_poly, (float(x), float(y)), False)
        return result >= 0

    def draw(self, frame: np.ndarray, color=(0, 255, 128), thickness=2) -> np.ndarray:
        """Draw zone outline on a frame (in-place copy)."""
        pts = self._np_poly.astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=thickness)
        # Semi-transparent fill
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], color)
        cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)
        # Zone label
        cx = int(np.mean(self._np_poly[:, 0]))
        cy = int(np.mean(self._np_poly[:, 1]))
        cv2.putText(frame, f"LPR:{self.id}", (cx - 30, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        return frame

    # ------------------------------------------------------------------
    @classmethod
    def from_config(cls, cfg: dict) -> "LPRZone":
        return cls(
            id=cfg["id"],
            polygon=[(float(p[0]), float(p[1])) for p in cfg["polygon"]],
        )


def build_zones(zone_configs: List[dict]) -> List[LPRZone]:
    return [LPRZone.from_config(c) for c in (zone_configs or [])]


def point_in_any_zone(zones: List[LPRZone], x: float, y: float) -> Optional[LPRZone]:
    """Return the first zone that contains the point, or None."""
    for z in zones:
        if z.contains(x, y):
            return z
    return None
