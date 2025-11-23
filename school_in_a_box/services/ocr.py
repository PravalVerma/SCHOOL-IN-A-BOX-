# services/ocr.py
"""
OCR utilities for School in a Box.

Uses Tesseract via pytesseract to extract text from images.
"""

from __future__ import annotations

from typing import Optional

from PIL import Image
import pytesseract
import io
import os
import platform


# Optional: set tesseract cmd explicitly on Windows if not in PATH
if platform.system() == "Windows":
    # TODO: update this path if your Tesseract is installed elsewhere
    default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_path):
        pytesseract.pytesseract.tesseract_cmd = default_path


def extract_text_from_image(image_bytes: bytes, lang: str = "eng") -> str:
    """
    Run OCR on an image (bytes) and return extracted text.

    - image_bytes: raw bytes from uploaded file
    - lang: OCR language code (default 'eng')
    """
    image = Image.open(io.BytesIO(image_bytes))
    text: str = pytesseract.image_to_string(image, lang=lang)
    return text.strip()
