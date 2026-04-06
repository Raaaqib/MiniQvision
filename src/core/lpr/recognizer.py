"""
LPR Recognizer — extracts text from a license plate crop using EasyOCR.

Normalisation rules (tweak per region/country):
  - Uppercase
  - Strip whitespace / hyphens / dots
  - Min length filter (plates are usually ≥ 2 chars)
"""

from __future__ import annotations
import logging
import re
import numpy as np
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class PlateRecognizer:
    """
    Wraps EasyOCR to read text from a pre-cropped plate image.

    Parameters
    ----------
    lang : str
        OCR language code.  Use 'en' for Latin plates; 'ar' for Arabic.
        EasyOCR language codes: https://www.jaided.ai/easyocr/
        NOTE: EasyOCR uses a list — 'en' becomes ['en'], 'ar' becomes ['ar','en']
    use_angle_cls : bool
        Not used by EasyOCR (kept for API compatibility with PaddleOCR version).
    use_gpu : bool
        Set True if a CUDA GPU is available.
    min_confidence : float
        Minimum OCR score to accept a reading.
    min_length : int
        Minimum character count after normalisation.
    """

    # Map single lang codes to EasyOCR language lists
    _LANG_MAP = {
        "en":  ["en"],
        "ar":  ["ar", "en"],
        "ch":  ["ch_sim", "en"],
        "fr":  ["fr", "en"],
        "de":  ["de", "en"],
        "es":  ["es", "en"],
    }

    def __init__(
        self,
        lang: str = "en",
        use_angle_cls: bool = True,
        use_gpu: bool = False,
        min_confidence: float = 0.60,
        min_length: int = 2,
    ):
        self.min_confidence = min_confidence
        self.min_length = min_length
        self._reader = None
        self._init_ocr(lang, use_gpu)

    # ------------------------------------------------------------------
    def _init_ocr(self, lang: str, use_gpu: bool):
        try:
            import easyocr
            langs = self._LANG_MAP.get(lang, ["en"])
            self._reader = easyocr.Reader(langs, gpu=use_gpu, verbose=False)
            logger.info(f"[LPR] EasyOCR initialised (langs={langs})")
        except ImportError:
            logger.error(
                "[LPR] easyocr not installed. "
                "Run: pip install easyocr"
            )
        except Exception as e:
            logger.error(f"[LPR] EasyOCR init failed: {e}")

    # ------------------------------------------------------------------
    def read(self, plate_crop: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Run OCR on a BGR plate crop.

        Returns
        -------
        (text, confidence)  — text is None if OCR failed or confidence too low.
        """
        if self._reader is None or plate_crop is None or plate_crop.size == 0:
            return None, 0.0

        # Upscale tiny crops — OCR accuracy drops below ~32px height
        h, w = plate_crop.shape[:2]
        if h < 32:
            scale = 32 / h
            import cv2
            plate_crop = cv2.resize(
                plate_crop,
                (int(w * scale), 32),
                interpolation=cv2.INTER_CUBIC,
            )

        try:
            # EasyOCR returns: [ (bbox, text, confidence), ... ]
            results = self._reader.readtext(plate_crop)
        except Exception as e:
            logger.warning(f"[LPR] OCR inference error: {e}")
            return None, 0.0

        if not results:
            return None, 0.0

        # Aggregate all text boxes — join by space, mean confidence
        texts, confs = [], []
        for (_bbox, text, conf) in results:
            texts.append(str(text))
            confs.append(float(conf))

        if not texts:
            return None, 0.0

        raw_text = " ".join(texts)
        avg_conf = sum(confs) / len(confs)

        normalised = self._normalise(raw_text)

        if avg_conf < self.min_confidence:
            logger.debug(
                f"[LPR] OCR confidence too low ({avg_conf:.2f}): '{normalised}'"
            )
            return None, avg_conf

        if len(normalised) < self.min_length:
            logger.debug(f"[LPR] OCR result too short: '{normalised}'")
            return None, avg_conf

        logger.debug(f"[LPR] Plate read: '{normalised}' ({avg_conf:.2f})")
        return normalised, avg_conf

    # ------------------------------------------------------------------
    @staticmethod
    def _normalise(text: str) -> str:
        """Uppercase, collapse whitespace, remove common separators."""
        text = text.upper()
        text = re.sub(r"[\s\-\.·•]", "", text)   # remove spaces, hyphens, dots
        text = re.sub(r"[^A-Z0-9\u0600-\u06FF]", "", text)  # keep alphanumeric + Arabic
        return text.strip()