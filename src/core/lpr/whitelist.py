"""
LPR Whitelist — manages known plates and triggers alerts for unknowns.

Plates are stored normalised (uppercase, no separators).
The whitelist is loaded from config at startup and can be updated at
runtime via the API (changes are persisted to the SQLite DB).
"""

from __future__ import annotations
import logging
import re
from typing import Set, Optional

logger = logging.getLogger(__name__)


def _normalise(plate: str) -> str:
    plate = plate.upper().strip()
    plate = re.sub(r"[\s\-\.]", "", plate)
    return plate


class PlateWhitelist:
    """
    In-memory whitelist with optional DB backing.

    Parameters
    ----------
    plates : list[str]
        Initial known plates from config.
    """

    def __init__(self, plates: Optional[list] = None):
        self._known: Set[str] = set()
        for p in (plates or []):
            self.add(p)
        logger.info(f"[LPR] Whitelist loaded with {len(self._known)} plate(s)")

    # ------------------------------------------------------------------
    def add(self, plate: str):
        norm = _normalise(plate)
        if norm:
            self._known.add(norm)
            logger.debug(f"[LPR] Whitelist ++ {norm}")

    def remove(self, plate: str):
        norm = _normalise(plate)
        self._known.discard(norm)
        logger.debug(f"[LPR] Whitelist -- {norm}")

    def is_known(self, plate: str) -> bool:
        return _normalise(plate) in self._known

    def is_unknown(self, plate: str) -> bool:
        return not self.is_known(plate)

    def all_plates(self) -> list:
        return sorted(self._known)

    def __len__(self) -> int:
        return len(self._known)

    # ------------------------------------------------------------------
    def check(self, plate: str) -> dict:
        """
        Returns a status dict for an observed plate.

        {
          "plate":   str,       # normalised plate text
          "known":   bool,
          "alert":   bool,      # True when unknown → triggers alert
        }
        """
        norm = _normalise(plate)
        known = norm in self._known
        return {
            "plate": norm,
            "known": known,
            "alert": not known,   # alert on UNKNOWN plates
        }
