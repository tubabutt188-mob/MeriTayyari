"""
OCR Test Script — Past Papers (Urdu + English)
================================================
Requirements (install these on your local machine first):

    pip install pytesseract pillow

Also install Tesseract OCR engine itself + language packs:

    # Windows: download installer from
    #   https://github.com/UB-Mannheim/tesseract/wiki
    #   (select "Urdu" + "English" during setup, or add urd.traineddata manually)

    # Mac:
    #   brew install tesseract tesseract-lang

    # Linux (Ubuntu/Debian):
    #   sudo apt install tesseract-ocr tesseract-ocr-urd tesseract-ocr-eng

Usage:
    python ocr_test.py data/past_papers/grade9/physics

This will OCR every image in that folder and save a matching .txt file
next to it, so you can manually check OCR quality.
"""

import sys
import os
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
except ImportError:
    print("Missing packages. Run: pip install pytesseract pillow")
    sys.exit(1)

# If Tesseract isn't on PATH (common on Windows), uncomment and set path:
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\tubab\AppData\Local\Tesseract-OCR\tesseract.exe"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".jfif", ".webp", ".bmp"}


def ocr_image(image_path: Path, lang: str = "eng+urd") -> str:
    """Run OCR on a single image and return extracted text."""
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang=lang)
    return text


def process_folder(folder: Path):
    images = [p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS]

    if not images:
        print(f"No images found in {folder}")
        return

    print(f"Found {len(images)} images. Starting OCR...\n")

    for img_path in images:
        print(f"Processing: {img_path.name}")
        try:
            text = ocr_image(img_path)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        out_path = img_path.with_suffix(".txt")
        out_path.write_text(text, encoding="utf-8")

        # Quick quality signal: how much text got extracted
        char_count = len(text.strip())
        status = "OK" if char_count > 50 else "LOW TEXT (check manually)"
        print(f"  -> {out_path.name} ({char_count} chars) [{status}]")

    print("\nDone. Open the .txt files next to each image to review quality.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ocr_test.py <folder_path>")
        sys.exit(1)

    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"Not a valid folder: {folder}")
        sys.exit(1)

    process_folder(folder)