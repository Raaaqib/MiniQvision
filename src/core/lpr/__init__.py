"""
Raaqib LPR (License Plate Recognition) sub-package.

Public API
----------
LPRManager   — top-level factory, call .process() from camera loop
LPRResult    — dataclass for a single plate recognition event
"""

from .manager import LPRManager
from .pipeline import LPRResult
from .zone import LPRZone, build_zones
from .whitelist import PlateWhitelist

__all__ = ["LPRManager", "LPRResult", "LPRZone", "build_zones", "PlateWhitelist"]
