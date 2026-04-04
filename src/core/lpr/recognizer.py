"""
LPR Recognizer — extracts text from a license plate crop using PaddleOCR.

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
    Wraps PaddleOCR to read text from a pre-cropped plate image.

    Parameters
    ----------
    lang : str
        OCR language code.  Use 'en' for Latin plates; 'ar' for Arabic;
        'ch' for Chinese, etc.  PaddleOCR supports 80+ languages.
    use_angle_cls : bool
        Rotate detection — useful for tilted plates.
    use_gpu : bool
        Set True if a CUDA GPU is available.
    min_confidence : float
        Minimum OCR score to accept a reading.
    min_length : int
        Minimum character count after normalisation.
    """

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
        self._ocr = None
        self._init_ocr(lang, use_angle_cls, use_gpu)

    # ------------------------------------------------------------------
    def _init_ocr(self, lang: str, use_angle_cls: bool, use_gpu: bool):
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=use_angle_cls,
                lang=lang,
                use_gpu=use_gpu,
                show_log=False,
            )
            logger.info(f"[LPR] PaddleOCR initialised (lang={lang})")
        except ImportError:
            logger.error(
                "[LPR] paddleocr not installed. "
                "Run: pip install paddleocr paddlepaddle"
            )
        except Exception as e:
            logger.error(f"[LPR] PaddleOCR init failed: {e}")

    # ------------------------------------------------------------------
    def read(self, plate_crop: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Run OCR on a BGR plate crop.

        Returns
        -------
        (text, confidence)  — text is None if OCR failed or confidence too low.
        """
        if self._ocr is None or plate_crop is None or plate_crop.size == 0:
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
            result = self._ocr.ocr(plate_crop, cls=True)
        except Exception as e:
            logger.warning(f"[LPR] OCR inference error: {e}")
            return None, 0.0

        if not result or not result[0]:
            return None, 0.0

        # Aggregate all text boxes — join by space, pick mean confidence
        texts, confs = [], []
        for line in result[0]:
            if line and len(line) == 2:
                text_conf = line[1]          # (text, score)
                if text_conf:
                    texts.append(str(text_conf[0]))
                    confs.append(float(text_conf[1]))

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
